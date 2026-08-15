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

!include nsDialogs.nsh

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

; ---- 卸载：提醒会清除所有数据（多语言文本）----
LangString MCE_UninstDataWarn 2052 "卸载将删除程序并清除所有数据（output 导出、data 设置、temp 缓存、logs 日志）。$\r$\n确定继续卸载吗？"
LangString MCE_UninstDataWarn 1033 "Uninstall will remove the app and delete all data (output exports, data settings, temp cache, logs).$\r$\nAre you sure you want to continue?"
LangString MCE_UninstDataWarn 1041 "アンインストールするとアプリとすべてのデータ（output 出力、data 設定、temp キャッシュ、logs ログ）が削除されます。$\r$\n続行しますか？"

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
  FunctionEnd
!macroend

; ---- 安装完成后：按用户选择移除未勾选的快捷方式 ----
; electron-builder 默认已创建快捷方式（createDesktopShortcut / createStartMenuShortcut
; 均为 true），customInstall 在 addStartMenuLink / addDesktopLink 之后执行，
; 因此这里根据复选框状态删除对应快捷方式。
; 静默安装（/S）不显示选项页 → 变量为空字符串 → 不删除，保持默认创建。
!macro customInstall
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

; ---- 卸载钩子：卸载前提醒会清除所有数据 ----
; customUnInstall 在 electron-builder 卸载器模板（uninstaller.nsh）中位于
; RMDir /r $INSTDIR 之前执行。此时尚未删除任何文件，若存在数据目录则提醒用户：
; 卸载会同时清除安装目录下的全部数据；用户选"否"→ Abort 取消卸载（文件原样保留）。
; - 静默卸载（/S）不询问，直接卸载；
; - 无数据目录时也不询问；
; - 全部用寄存器/逻辑块，不声明 Var（避免 -WX 对"未引用变量"报错）。
!macro customUnInstall
  ${IfNot} ${Silent}
    ${If} ${FileExists} "$INSTDIR\output\*.*"
    ${OrIf} ${FileExists} "$INSTDIR\data\*.*"
    ${OrIf} ${FileExists} "$INSTDIR\temp\*.*"
    ${OrIf} ${FileExists} "$INSTDIR\logs\*.*"
      MessageBox MB_YESNO|MB_ICONEXCLAMATION "$(MCE_UninstDataWarn)" IDYES MCE_uninstall_continue
      Abort   ; 用户选择"否"→ 取消卸载（此时尚未删除任何文件）
      MCE_uninstall_continue:
    ${EndIf}
  ${EndIf}
!macroend
