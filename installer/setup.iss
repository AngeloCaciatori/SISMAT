; =============================================================================
;  SISMAT — Script de Instalação (Inno Setup 6)
;  Bia C AD/5 — Subtenência / Reserva de Material
;  Versão 1.0.0
; =============================================================================

#define MyAppName      "SISMAT"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Bia C AD/5 — Subtenência"
#define MyAppExe       "iniciar.bat"
#define MyAppURL       ""
#define MyOutputBase   "Setup_SISMAT_1.0.0"

[Setup]
AppId={{B5C2A1D4-9E3F-4C7B-8A6D-1F2E3D4C5B6A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\SISMAT
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
LicenseFile=docs\LICENCA.txt
OutputDir=Output
OutputBaseFilename={#MyOutputBase}
SetupIconFile=brasao.ico
WizardImageFile=wizard_large.png
WizardSmallImageFile=wizard_small.png
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
; Páginas do wizard
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
brazilianportuguese.WelcomeLabel1=Bem-vindo ao instalador do {#MyAppName}
brazilianportuguese.WelcomeLabel2=Este assistente irá instalar o {#MyAppName} versão {#MyAppVersion} no seu computador.%n%nSistema de Controle de Material — Bia C AD/5%nSubtenência / Reserva de Material%n%nRecomenda-se fechar todos os outros programas antes de continuar.%n%nClique em Avançar para continuar.
brazilianportuguese.FinishedLabel=A instalação do {#MyAppName} foi concluída com sucesso.%n%nPara iniciar o sistema, clique em "Iniciar SISMAT" na Área de Trabalho ou no Menu Iniciar.%n%nAcesse pelo navegador: http://localhost:5000%n(ou pelo IP do servidor na rede local)

; =============================================================================
;  COMPONENTES
; =============================================================================
[Components]
Name: "base";        Description: "SISMAT — Aplicação principal (obrigatório)"; Types: full compact custom; Flags: fixed
Name: "importlegado"; Description: "Importar dados legados (CSVs do sistema anterior)"; Types: full; Flags: checkablealone

; =============================================================================
;  TAREFAS
; =============================================================================
[Tasks]
Name: "desktopicon";   Description: "Criar atalho na Área de Trabalho";    GroupDescription: "Atalhos:"; Flags: checkedonce
Name: "startmenu";     Description: "Criar atalho no Menu Iniciar";         GroupDescription: "Atalhos:"; Flags: checkedonce
Name: "firewall";      Description: "Liberar porta 5000 no Firewall Windows (acesso pela rede local)"; GroupDescription: "Rede:"; Flags: checkedonce
Name: "backupmensal";  Description: "Agendar backup automático mensal (dia 1 às 03:00)"; GroupDescription: "Manutenção:"; Flags: unchecked

; =============================================================================
;  ARQUIVOS
; =============================================================================
[Files]
; Aplicacao principal
Source: "app_source\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: base

; Instalador do Python (copiado para temp, apagado apos instalar)
; So incluido se o arquivo existir na pasta python_installer\
Source: "python_installer\python-3.12.7-amd64.exe"; DestDir: "{tmp}"; \
  Flags: ignoreversion deleteafterinstall; Components: base; \
  Check: PythonInstallerDisponivel

; Pacotes Python offline
Source: "wheels\*"; DestDir: "{app}\wheels"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: base

; Documentacao
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: base

; Icone
Source: "brasao.ico"; DestDir: "{app}"; Flags: ignoreversion; Components: base

; =============================================================================
;  ÍCONES (ATALHOS)
; =============================================================================
[Icons]
; Área de trabalho
Name: "{autodesktop}\Iniciar SISMAT";    Filename: "{app}\iniciar.bat"; IconFilename: "{app}\brasao.ico"; Tasks: desktopicon
; Menu Iniciar
Name: "{group}\Iniciar SISMAT";          Filename: "{app}\iniciar.bat"; IconFilename: "{app}\brasao.ico"; Tasks: startmenu
Name: "{group}\Manual do Usuário";       Filename: "{app}\docs\MANUAL_RAPIDO.md"; Tasks: startmenu
Name: "{group}\Desinstalar SISMAT";      Filename: "{uninstallexe}"; Tasks: startmenu

; =============================================================================
;  EXECUÇÃO PÓS-INSTALAÇÃO
; =============================================================================
[Run]
; PASSO 0 — Instalar Python silenciosamente se nao estiver no PC
; (so roda se o instalador do Python foi incluido E Python nao esta instalado)
Filename: "{tmp}\python-3.12.7-amd64.exe"; \
  Parameters: "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_launcher=1"; \
  StatusMsg: "Instalando Python 3.12 (aguarde, pode demorar)..."; \
  Flags: waituntilterminated; Components: base; \
  Check: DeveInstalarPython

; PASSO UNICO — configurar.bat detecta Python do sistema e configura tudo
Filename: "{cmd}"; \
  Parameters: "/c ""{app}\scripts\configurar.bat"""; \
  WorkingDir: "{app}"; StatusMsg: "Configurando Python e banco de dados (aguarde)..."; \
  Flags: waituntilterminated; Components: base

; Importar dados legados (se componente selecionado)
Filename: "{app}\.venv\Scripts\python.exe"; \
  Parameters: """{app}\scripts\importar_legado.py"""; \
  WorkingDir: "{app}"; StatusMsg: "Importando dados do sistema anterior..."; \
  Flags: runhidden waituntilterminated; Components: importlegado

; Regra de firewall (se tarefa selecionada)
Filename: "{cmd}"; \
  Parameters: "/c netsh advfirewall firewall add rule name=""SISMAT 5000"" dir=in action=allow protocol=TCP localport=5000"; \
  StatusMsg: "Liberando porta 5000 no firewall..."; \
  Flags: runhidden waituntilterminated; Tasks: firewall

; Tarefa agendada de backup mensal (se selecionada)
Filename: "{cmd}"; \
  Parameters: "/c schtasks /Create /F /TN ""SISMAT Backup Mensal"" /SC MONTHLY /D 1 /ST 03:00 /TR ""{app}\scripts\backup_mensal.bat"""; \
  StatusMsg: "Agendando backup mensal automatico..."; \
  Flags: runhidden waituntilterminated; Tasks: backupmensal

; Abrir o SISMAT ao final (opcional)
Filename: "{app}\iniciar.bat"; Description: "Iniciar o SISMAT agora"; \
  Flags: nowait postinstall skipifsilent; Components: base

; =============================================================================
;  EXCLUSÕES NA DESINSTALAÇÃO
; =============================================================================
[UninstallDelete]
; Remover o ambiente virtual (grande, não é dado do usuário)
Type: filesandordirs; Name: "{app}\.venv"
; Remover wheels (já instalados, não precisam ficar)
Type: filesandordirs; Name: "{app}\wheels"

; NOTA: instance\sismat.db e instance\backups\ são preservados por padrão.
; O código abaixo pergunta se o usuário quer apagar os dados também.

; =============================================================================
;  CÓDIGO PASCAL — LÓGICA CUSTOMIZADA
; =============================================================================
[Code]

// ─── Detectar se Python esta instalado no sistema ─────────────────────────────
function PythonEstaInstalado: Boolean;
var
  PythonPath: String;
begin
  // Verifica pelo Python Launcher (py.exe) - instalado por padrao
  Result := FileExists(ExpandConstant('{sys}\py.exe'));
  if Result then Exit;

  // Verifica caminhos comuns de instalacao
  Result := FileExists('C:\Python312\python.exe') or
            FileExists('C:\Python311\python.exe') or
            FileExists('C:\Python310\python.exe') or
            FileExists(ExpandConstant('{localappdata}\Programs\Python\Python312\python.exe')) or
            FileExists(ExpandConstant('{localappdata}\Programs\Python\Python311\python.exe'));
  if Result then Exit;

  // Verifica registro (instalacao para todos os usuarios)
  Result := RegValueExists(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Python\PythonCore\3.12\InstallPath', '');
  if Result then Exit;
  Result := RegValueExists(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Python\PythonCore\3.11\InstallPath', '');
  if Result then Exit;

  // Verifica registro (instalacao para usuario atual)
  Result := RegValueExists(HKEY_CURRENT_USER,
    'SOFTWARE\Python\PythonCore\3.12\InstallPath', '');
  if Result then Exit;
  Result := RegValueExists(HKEY_CURRENT_USER,
    'SOFTWARE\Python\PythonCore\3.11\InstallPath', '');
end;

// ─── O arquivo instalador do Python esta na pasta python_installer? ───────────
function PythonInstallerDisponivel: Boolean;
begin
  Result := FileExists(ExpandConstant('{src}\python_installer\python-3.12.7-amd64.exe'));
end;

// ─── Deve instalar Python? (tem o arquivo E Python nao esta no sistema) ────────
function DeveInstalarPython: Boolean;
begin
  Result := PythonInstallerDisponivel and not PythonEstaInstalado;
end;

// ─── Desinstalação: perguntar sobre banco de dados ────────────────────────────
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Resposta: Integer;
  DbPath: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    DbPath := ExpandConstant('{app}\instance');
    if DirExists(DbPath) then
    begin
      Resposta := MsgBox(
        'Deseja apagar TAMBÉM o banco de dados (sismat.db) e os backups?' + #13#10 + #13#10 +
        '  • Clique em NÃO para manter seus dados (recomendado se planeja reinstalar).' + #13#10 +
        '  • Clique em SIM apenas se quiser apagar tudo permanentemente.' + #13#10 + #13#10 +
        'ATENÇÃO: esta ação não pode ser desfeita.',
        mbConfirmation,
        MB_YESNO or MB_DEFBUTTON2  // padrão = NÃO
      );
      if Resposta = IDYES then
      begin
        DelTree(DbPath, True, True, True);
        MsgBox('Banco de dados e backups removidos.', mbInformation, MB_OK);
      end else begin
        MsgBox('Dados preservados em: ' + DbPath, mbInformation, MB_OK);
      end;
    end;
  end;
end;

