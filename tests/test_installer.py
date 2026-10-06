"""Optional Windows NSIS macro tests, restricted to disposable fixture directories."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MAKENSIS = os.environ.get('MCE_TEST_MAKENSIS', '')
REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt' and MAKENSIS and Path(MAKENSIS).is_file(),
                     'Set MCE_TEST_MAKENSIS to enable isolated Windows NSIS tests')
class InstallerMacros(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='mce-nsis-test-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()

    def fixture(self, commands):
        # The included source only defines macros and strings. Only the specified
        # backup/restore macros execute; no application installer/uninstaller hooks run.
        script = self.root / 'fixture.nsi'
        executable = self.root / 'fixture.exe'
        script.write_text(f'''Unicode true
Name "MCE disposable macro fixture"
OutFile "{executable}"
RequestExecutionLevel user
SilentInstall silent
!include "LogicLib.nsh"
!include "MUI2.nsh"
!include "{REPO / 'electron/nsis/installer.nsh'}"
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "Japanese"
!insertmacro customHeader
Section
{commands}
SectionEnd
''', encoding='utf-8-sig')
        env = dict(os.environ)
        env.setdefault('NSISDIR', str(Path(MAKENSIS).parent.parent))
        compiled = subprocess.run([MAKENSIS, '/V2', str(script)], env=env, capture_output=True,
                                  text=True, errors='replace', timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        self.assertTrue(executable.is_file())
        return subprocess.run([str(executable), '/S'], capture_output=True, timeout=30,
                              creationflags=subprocess.CREATE_NO_WINDOW)

    def files(self, directory):
        directory.mkdir(parents=True)
        (directory / 'preset.json').write_text('preserved preset', encoding='utf-8')
        (directory / 'settings.json').write_text('preserved settings', encoding='utf-8')

    def test_restore_rename_success(self):
        source, target = self.root / 'backup', self.root / 'restored'
        self.files(source)
        result = self.fixture(f'!insertmacro MCE_RestoreDirMove "{source}" "{target}"')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(source.exists())
        self.assertEqual((target / 'preset.json').read_text(), 'preserved preset')

    def test_restore_copy_success_merges_then_removes_backup(self):
        source, target = self.root / 'backup', self.root / 'restored'
        self.files(source)
        target.mkdir()
        (target / 'other.txt').write_text('keep existing')
        result = self.fixture(f'!insertmacro MCE_RestoreDirMove "{source}" "{target}"')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(source.exists())
        self.assertEqual((target / 'preset.json').read_text(), 'preserved preset')
        self.assertEqual((target / 'other.txt').read_text(), 'keep existing')

    def test_restore_copy_failure_preserves_entire_backup(self):
        source = self.root / 'backup'
        self.files(source)
        blocker = self.root / 'blocked-parent'
        blocker.write_text('a file cannot be a destination directory')
        target = blocker / 'restored'
        result = self.fixture(f'!insertmacro MCE_RestoreDirMove "{source}" "{target}"')
        self.assertEqual(result.returncode, 0)
        self.assertEqual((source / 'preset.json').read_text(), 'preserved preset')
        self.assertEqual((source / 'settings.json').read_text(), 'preserved settings')

    def test_backup_copy_failure_stops_install_and_restores_previous_moves(self):
        previous, backup = self.root / 'previous', self.root / 'backup'
        self.files(previous / 'data')
        self.files(previous / 'output')
        backup.mkdir()
        blocker = self.root / 'blocked-parent'
        blocker.write_text('force copy failure')
        sentinel = self.root / 'installation-continued.txt'
        commands = f'''StrCpy $MCE_PrevDir "{previous}"
StrCpy $MCE_BackupDir "{backup}"
!insertmacro MCE_BackupDirMove "{previous / 'data'}" "{backup / 'data'}"
!insertmacro MCE_BackupDirMove "{previous / 'output'}" "{blocker / 'output'}"
FileOpen $1 "{sentinel}" w
FileWrite $1 "should never execute"
FileClose $1'''
        result = self.fixture(commands)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(sentinel.exists())
        for category in ['data', 'output']:
            self.assertEqual((previous / category / 'preset.json').read_text(), 'preserved preset')


if __name__ == '__main__':
    unittest.main()
