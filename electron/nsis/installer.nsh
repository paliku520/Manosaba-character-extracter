; ============================================================
; MCE 自定义安装选项页面（assisted installer 专用）
;
; 在"选择安装目录"之后、"开始安装"之前，让用户勾选：
;   ☑ 创建桌面快捷方式
;   ☑ 添加到开始菜单
;
; 支持语言：简体中文 / English / 日本語
; （文本使用数字 LCID 定义 LangString：2052=中文 / 1033=英文 / 1041=日文，
;   不依赖 MUI_LANGUAGE 的展开顺序，可与 electron-builder 的 installerLanguages 共存）
; ============================================================
; 另一件事：用户数据保护（data / output / temp / logs）——对齐 Inno Setup 的行为
;
; 背景：electron-builder 的安装器在"覆盖更新"时并不是单纯覆盖文件，而是先**静默**运行
;   上一版写下的 Uninstall.exe（installUtil.nsh：`Uninstall.exe /S --updated _?=$INSTDIR`），
;   而卸载器默认以 `RMDir /r $INSTDIR` 收尾 —— 安装目录根下的用户数据会被一起删掉。
;   更麻烦的是：执行的是**旧版本编译出来的卸载器**，改本文件管不到它，只对下一次更新生效。
;
; 因此采用两层保护：
;   1) 卸载器：定义 customRemoveFiles，按**白名单**只删安装器写进去的文件
;      （resources / locales / swiftshader + 根目录的 MCE.exe、Uninstall、Chromium 载荷），
;      用户数据 data/output/temp/logs 保留，安装目录里用户自己放的文件一律不动 ——
;      即 Inno Setup 的语义：卸载/升级只动自己装进去的东西，绝不 `RMDir /r $INSTDIR`。
;      只有用户在卸载时选"一并删除数据"（或命令行 --delete-app-data）才删用户数据。
;   2) 安装器：安装开始前把用户数据搬到安装目录**同级**的备份目录（MCE-update-backup），
;      装完在 customInstall 里搬回。旧卸载器只删 $INSTDIR，碰不到同级目录 → 这一步专门兜住
;      "从旧版本升级"的过渡；对已装过新版卸载器的机器只是双保险（Rename 同盘瞬时完成，不搬数据）。
; ============================================================

!include nsDialogs.nsh

; ---- 用户数据备份目录名（$INSTDIR 的同级目录，形如 C:\Program Files\MCE-update-backup）----
!define MCE_BACKUP_DIRNAME "MCE-update-backup"

; 安装器专用变量（自定义 include 会被前置到主脚本开头，所以只能在顶层声明）：
;   $MCE_PrevDir   上次安装目录（备份源）
;   $MCE_BackupDir 本次备份目录
; 卸载器编译（BUILD_UNINSTALLER）时不声明，避免 -WX 把"变量未引用"警告当错误。
!ifndef BUILD_UNINSTALLER
  Var MCE_PrevDir
  Var MCE_BackupDir
!endif

; ---- 把目录搬到备份位置（安装器专用）----
; ① 优先 Rename：同盘瞬时完成，不搬数据；
; ② 失败（目录里有文件被占用，如后端仍在写日志；或跨盘）→ xcopy 递归复制一份；
;    源目录**不删**：复制不完整或安装中途失败时，用户数据仍原地保留（旧卸载器随后会清理）。
!macro MCE_BackupDirMove FROM TO
  ${If} ${FileExists} "${FROM}\*.*"
    ClearErrors
    Rename "${FROM}" "${TO}"
    ${If} ${Errors}
      DetailPrint "Backup: ${FROM} is busy, copying..."
      nsExec::ExecToLog 'xcopy /E /I /H /R /Y /Q "${FROM}" "${TO}"'
      Pop $0
    ${EndIf}
  ${EndIf}
!macroend

; ---- 把备份搬回安装目录（安装器专用）----
; 目标已存在（上次取消安装 / 旧卸载器删不掉的残留）→ Rename 失败 → xcopy 合并覆盖；
; 复制成功后再清理备份，避免下次安装把过期数据又盖回去。
!macro MCE_RestoreDirMove FROM TO
  ${If} ${FileExists} "${FROM}\*.*"
    ClearErrors
    Rename "${FROM}" "${TO}"
    ${If} ${Errors}
      DetailPrint "Restore: merging ${FROM}..."
      nsExec::ExecToLog 'xcopy /E /I /H /R /Y /Q "${FROM}" "${TO}"'
      Pop $0
      RMDir /r "${FROM}"
    ${EndIf}
  ${EndIf}
!macroend

; ---- 备份用户数据（安装器专用；幂等：源目录已被搬走时什么都不做）----
; 源目录取注册表里的上次安装位置 —— 用户若在目录页改了安装目录，数据仍在旧目录里；
; 备份目录放在旧安装目录的同级，保证落在同一个卷上，Rename 才有效。
!macro MCE_BackupUserData
  ${If} $MCE_BackupDir == ""
    ReadRegStr $MCE_PrevDir SHELL_CONTEXT "${INSTALL_REGISTRY_KEY}" "InstallLocation"
    ${If} $MCE_PrevDir == ""
      StrCpy $MCE_PrevDir "$INSTDIR"
    ${EndIf}
    StrCpy $MCE_BackupDir "$MCE_PrevDir\..\${MCE_BACKUP_DIRNAME}"
  ${EndIf}
  CreateDirectory "$MCE_BackupDir"

  !insertmacro MCE_BackupDirMove "$MCE_PrevDir\data"   "$MCE_BackupDir\data"
  !insertmacro MCE_BackupDirMove "$MCE_PrevDir\output" "$MCE_BackupDir\output"
  !insertmacro MCE_BackupDirMove "$MCE_PrevDir\temp"   "$MCE_BackupDir\temp"
  !insertmacro MCE_BackupDirMove "$MCE_PrevDir\logs"   "$MCE_BackupDir\logs"
!macroend

; ---- 还原用户数据（安装器专用）----
; $MCE_BackupDir 为空（本次没备份，例如上次安装失败/取消后重跑）时，退回按当前安装目录
; 推算备份路径 —— 这样上一次遗留的备份会在下一次成功安装时自动还原。
!macro MCE_RestoreUserData
  ${If} $MCE_BackupDir == ""
    StrCpy $MCE_BackupDir "$INSTDIR\..\${MCE_BACKUP_DIRNAME}"
  ${EndIf}
  !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\data"   "$INSTDIR\data"
  !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\output" "$INSTDIR\output"
  !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\temp"   "$INSTDIR\temp"
  !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\logs"   "$INSTDIR\logs"
  RMDir "$MCE_BackupDir"   ; 已清空才删得掉；有残留就留着，方便人工检查
!macroend

; ---- 安装器 .onInit：没有页面可兜底的场景只能在这里提前备份 ----
; 静默安装（/S --updated，自动更新/脚本调用）和 one-click 安装都不会进入任何页面；
; assisted 交互安装则推迟到"选项页离开"时做（紧邻安装，用户中途取消不会先搬走数据）。
!macro customInit
  !ifdef ONE_CLICK
    !insertmacro MCE_BackupUserData
  !else
    ${If} ${Silent}
      !insertmacro MCE_BackupUserData
    ${EndIf}
  !endif
!macroend

; ---- customHeader：插在 installer.nsi 的 .onInit 之前（此时 MUI2/多用户等定义已就绪）----
; 兜底还原：用户中途取消安装、或安装结束时备份还在，就把用户数据搬回**原安装目录**
; （$MCE_PrevDir，即上次安装位置；用户可能已改了新的安装目录，数据应回到程序还在的地方）。
; 正常安装结束时备份已在 customInstall 里搬走 → 这里自然什么都不做（幂等，可重复调用）。
; ⚠ 不要定义 .onUserAbort：assisted installer 会 include UAC.nsh，其中已定义该回调，
;    重复定义会让 makensis 直接失败（Function named ".onUserAbort" already exists）。
;    用户取消/中止安装时同样会走到 .onGUIEnd（installer.nsh 的 abort 路径也会触发它）。
!macro customHeader
  !ifndef BUILD_UNINSTALLER
    Function MCE_RestoreOnAbort
      ${If} $MCE_BackupDir != ""
        !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\data"   "$MCE_PrevDir\data"
        !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\output" "$MCE_PrevDir\output"
        !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\temp"   "$MCE_PrevDir\temp"
        !insertmacro MCE_RestoreDirMove "$MCE_BackupDir\logs"   "$MCE_PrevDir\logs"
        RMDir "$MCE_BackupDir"
      ${EndIf}
    FunctionEnd

    Function .onGUIEnd
      Call MCE_RestoreOnAbort
    FunctionEnd
  !endif
!macroend

; ---- 多语言文本 ----
LangString MCE_OptionsPage_Title 2052 "选择安装选项"
LangString MCE_OptionsPage_Title 1033 "Choose Installation Options"
LangString MCE_OptionsPage_Title 1041 "インストールオプションの選択"

LangString MCE_OptionsPage_Subtitle 2052 "请选择要创建的快捷方式。"
LangString MCE_OptionsPage_Subtitle 1033 "Select the shortcuts to create."
LangString MCE_OptionsPage_Subtitle 1041 "作成するショートカットを選択してください。"

LangString MCE_CreateDesktop 2052 "创建桌面快捷方式"
LangString MCE_CreateDesktop 1033 "Create desktop shortcut"
LangString MCE_CreateDesktop 1041 "デスクトップにショートカットを作成"

LangString MCE_CreateStartMenu 2052 "添加到开始菜单"
LangString MCE_CreateStartMenu 1033 "Add to Start Menu"
LangString MCE_CreateStartMenu 1041 "スタートメニューに追加"

; ---- 卸载：询问是否一并删除用户数据（多语言文本）----
; 三选一：是 = 连用户数据一起删；否 = 只卸载程序、保留数据（Inno Setup 默认语义）；取消 = 中止卸载。
LangString MCE_UninstDataAsk 2052 "卸载将删除程序文件（MCE.exe / resources / locales 等），不会自动删除用户数据。$\r$\n是否同时删除用户数据（output 导出、data 设置、temp 缓存、logs 日志）？$\r$\n$\r$\n[是] 一并删除，不可恢复$\r$\n[否] 只卸载程序，保留数据$\r$\n[取消] 中止卸载"
LangString MCE_UninstDataAsk 1033 "Uninstall removes the program files (MCE.exe / resources / locales, etc.); user data is never removed automatically.$\r$\nDelete user data too (output exports, data settings, temp cache, logs)?$\r$\n$\r$\n[Yes] delete everything (cannot be undone)$\r$\n[No] uninstall the app only, keep my data$\r$\n[Cancel] abort uninstall"
LangString MCE_UninstDataAsk 1041 "アンインストールではプログラム本体（MCE.exe / resources / locales など）を削除します。ユーザーデータは自動では削除しません。$\r$\nユーザーデータ（output 出力、data 設定、temp キャッシュ、logs ログ）も削除しますか？$\r$\n$\r$\n[はい] すべて削除（復元できません）$\r$\n[いいえ] プログラムのみ削除し、データは残す$\r$\n[キャンセル] アンインストールを中止"

; ---- 安装选项页面（electron-builder assisted installer 钩子）----
; 宏体在 assistedInstaller.nsh 中展开，此时 MUI2.nsh / nsDialogs.nsh 均已加载。
; 变量也声明在宏内：卸载器编译（BUILD_UNINSTALLER）时不展开此宏，
; 避免 electron-builder 的 warningsAsErrors（-WX）把"变量未引用"警告当错误。
!macro customPageAfterChangeDir
  Var MCE_DesktopCheckbox
  Var MCE_StartMenuCheckbox
  Var MCE_DesktopShortcut
  Var MCE_StartMenuShortcut

  Page custom MCEOptionsPage MCEOptionsPageLeave

  Function MCEOptionsPage
    !insertmacro MUI_HEADER_TEXT "$(MCE_OptionsPage_Title)" "$(MCE_OptionsPage_Subtitle)"
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
      Abort
    ${EndIf}

    ${NSD_CreateCheckbox} 0 0 100% 12u "$(MCE_CreateDesktop)"
    Pop $MCE_DesktopCheckbox
    ${NSD_SetState} $MCE_DesktopCheckbox ${BST_CHECKED}

    ${NSD_CreateCheckbox} 0 24u 100% 12u "$(MCE_CreateStartMenu)"
    Pop $MCE_StartMenuCheckbox
    ${NSD_SetState} $MCE_StartMenuCheckbox ${BST_CHECKED}

    nsDialogs::Show
  FunctionEnd

  Function MCEOptionsPageLeave
    ${NSD_GetState} $MCE_DesktopCheckbox $0
    StrCpy $MCE_DesktopShortcut $0
    ${NSD_GetState} $MCE_StartMenuCheckbox $0
    StrCpy $MCE_StartMenuShortcut $0

    ; 本页紧邻"安装"页（customPageAfterChangeDir 就插在 MUI_PAGE_INSTFILES 之前）：
    ; 在这里备份用户数据，用户若在这之前取消安装则数据不受影响。
    ; （静默 / one-click 安装不进入页面，已在 customInit 里备份过）
    !insertmacro MCE_BackupUserData
  FunctionEnd
!macroend

; ---- 安装完成后：按用户选择移除未勾选的快捷方式 ----
; electron-builder 默认已创建快捷方式（createDesktopShortcut / createStartMenuShortcut
; 均为 true），customInstall 在 addStartMenuLink / addDesktopLink 之后执行，
; 因此这里根据复选框状态删除对应快捷方式。
; 静默安装（/S）不显示选项页 → 变量为空字符串 → 不删除，保持默认创建。
!macro customInstall
  ; ── 还原更新前的用户数据（见文件顶部说明）────────────────────
  ; 放在 icacls 之前：还原出来的 data/output/temp/logs 也能一并拿到 Users 写权限。
  !insertmacro MCE_RestoreUserData

  ${If} $MCE_DesktopShortcut == "0"
    Delete "$newDesktopLink"
  ${EndIf}
  ${If} $MCE_StartMenuShortcut == "0"
    Delete "$newStartMenuLink"
  ${EndIf}

  ; ── 授予安装目录普通用户写权限（方案 2）────────────────────
  ; 目的：安装到 C:\Program Files 等受保护目录时，普通（非管理员）启动也能写
  ; data/output/temp/logs → 数据落在安装目录根（main.js dataDir() 探测可写，
  ; 不再回退到 %APPDATA%），且无需提权（不弹 UAC）。
  ; *S-1-5-32-545 = BUILTIN\Users（SID 形式，语言无关）；
  ; (OI)(CI)F = 对象/容器继承 + 完全控制（运行时新建的 data/output/temp/logs 自动继承）；
  ; /T 递归处理已存在的文件（覆盖此前以管理员运行产生的旧数据目录）。
  ; 说明：nsExec 静默执行（不弹控制台窗口）；失败不阻断安装（数据仍会回退 %APPDATA%，功能可用）。
  nsExec::ExecToLog 'icacls "$INSTDIR" /grant *S-1-5-32-545:(OI)(CI)F /T /Q'
  Pop $0
!macroend

; ---- 卸载器初始化：提醒会清除数据 + 决定"是否连数据一起删" ----
; 为什么放在 customUnInit（un.onInit 末尾）而不是 customUnInstall：
;   ① un.onInit 在卸载器模板里位于 un. 段落之前，一定早于 customRemoveFiles；
;      而 customUnInstall 的插入位置在各版本模板里并不一致（有的版本排在删除文件之后），
;      标志会来不及被 customRemoveFiles 读到；
;   ② /S 解析与 initMultiUser 都在它之前完成 → $INSTDIR / ${Silent} 已可靠。
; 行为（Inno Setup 风格的三选一）：有数据目录且非静默 → 询问用户：
;   选"是"→ $MCE_PurgeData=1，customRemoveFiles 连用户数据一起删除；
;   选"否"→ 保留用户数据，继续卸载；
;   选"取消"→ Quit 中止卸载（此时尚未删除任何文件；.onInit 里要用 Quit，Abort 只终止回调）。
; 静默卸载（/S，含"覆盖更新"时安装器调用的旧卸载器）不询问 → 保留用户数据。
; Var 必须在使用它的宏之前声明：customUnInit 最早，且 /GLOBAL 才能被 customRemoveFiles 读到。
!macro customUnInit
  Var /GLOBAL MCE_PurgeData
  StrCpy $MCE_PurgeData "0"

  ${IfNot} ${Silent}
    ${If} ${FileExists} "$INSTDIR\output\*.*"
    ${OrIf} ${FileExists} "$INSTDIR\data\*.*"
    ${OrIf} ${FileExists} "$INSTDIR\temp\*.*"
    ${OrIf} ${FileExists} "$INSTDIR\logs\*.*"
      MessageBox MB_YESNOCANCEL|MB_ICONEXCLAMATION "$(MCE_UninstDataAsk)" /SD IDNO IDYES MCE_uninstall_purge IDCANCEL MCE_uninstall_abort
      Goto MCE_uninstall_keep   ; 否 → 只卸载程序，保留用户数据
      MCE_uninstall_abort:
      Quit                      ; 取消 → 中止卸载（尚未删除任何文件）
      MCE_uninstall_purge:
      StrCpy $MCE_PurgeData "1" ; 是 → 连用户数据一起删除
      MCE_uninstall_keep:
    ${EndIf}
  ${EndIf}
!macroend

; ---- 删除已安装文件（白名单，Inno Setup 语义）----
; 只删下面这些**明确属于本程序**的条目，绝不 `RMDir /r $INSTDIR` ——
; 安装目录里用户自己放的文件/目录一律不动（宁可有残留，不误删）。
; 用户数据 data/output/temp/logs 默认保留，只有两种情形才删：
;   ① 交互卸载时用户选"是"（$MCE_PurgeData=1）；② 命令行显式 --delete-app-data。
; 覆盖更新走的是 `Uninstall.exe /S --updated`（无提示）→ 只清程序文件、保留数据。
; 被占用而删不掉的文件与模板原行为一致：留在原地，不阻断卸载。
!macro customRemoveFiles
  SetOutPath $TEMP   ; 当前目录仍指向 $INSTDIR 时，卸载器删不掉自己

  ; ── ① 程序目录（electron-builder / Electron 固定结构）──
  RMDir /r "$INSTDIR\resources"    ; app 载荷：app.asar / app.asar.unpacked / backend（Python 后端）
  RMDir /r "$INSTDIR\locales"      ; Chromium 语言包
  RMDir /r "$INSTDIR\swiftshader"  ; 旧版 Electron 的 SwiftShader 目录（存在才删）

  ; ── ② 根目录载荷：按扩展名删（这几类文件在安装目录里只可能是程序自带）──
  Delete "$INSTDIR\*.dll"          ; d3dcompiler_47 / ffmpeg / libEGL / libGLESv2 / vk_swiftshader / vulkan-1
  Delete "$INSTDIR\*.pak"          ; chrome_100_percent / chrome_200_percent / resources.pak
  Delete "$INSTDIR\*.bin"          ; snapshot_blob.bin / v8_context_snapshot.bin
  Delete "$INSTDIR\*.dat"          ; icudtl.dat

  ; ── ③ 零散文件按名字删（刻意不用 *.html / *.json 通配，避免误删用户文件）──
  Delete "$INSTDIR\version"                    ; Chromium 版本标记
  Delete "$INSTDIR\LICENSES.chromium.html"     ; Chromium 许可
  Delete "$INSTDIR\vk_swiftshader_icd.json"    ; Vulkan ICD 描述
  Delete "$INSTDIR\${APP_EXECUTABLE_FILENAME}" ; 主程序（MCE.exe）
  Delete "$INSTDIR\${UNINSTALL_FILENAME}"      ; 卸载器自身（模板原行为也会删除它）
  !ifdef UNINSTALLER_ICON
    Delete "$INSTDIR\uninstallerIcon.ico"
  !endif

  ; ── ④ 用户数据：默认保留，仅用户确认时删 ──
  StrCpy $R2 "1"     ; 1 = 保留用户数据
  ${If} $MCE_PurgeData == "1"
    StrCpy $R2 "0"
  ${EndIf}
  ClearErrors
  ${GetParameters} $R0
  ${GetOptions} $R0 "--delete-app-data" $R1
  ${IfNot} ${Errors}
    StrCpy $R2 "0"
  ${EndIf}
  ${If} $R2 == "0"
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\output"
    RMDir /r "$INSTDIR\temp"
    RMDir /r "$INSTDIR\logs"
  ${EndIf}

  ; ── ⑤ 目录已空（无用户数据、也没用户自有文件）时顺手删掉；非空会失败，正常 ──
  RMDir "$INSTDIR"
!macroend
