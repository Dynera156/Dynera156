@echo off

:: Get current folder
set "currentDir=%~dp0"
set "targetExe=%currentDir%downloader.exe"

echo Target: %targetExe%

if not exist "%targetExe%" (
    echo downloader.exe NOT found
    pause
    exit
)

echo Found downloader.exe

:: Create temporary VBScript
set "vbsFile=%temp%\createShortcut.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%vbsFile%"
echo strStartup = WshShell.SpecialFolders("Startup") >> "%vbsFile%"
echo Set oLink = WshShell.CreateShortcut(strStartup ^& "\downloader.lnk") >> "%vbsFile%"
echo oLink.TargetPath = "%targetExe%" >> "%vbsFile%"
echo oLink.WorkingDirectory = "%currentDir%" >> "%vbsFile%"
echo oLink.Save >> "%vbsFile%"

:: Run VBScript
cscript //nologo "%vbsFile%"

:: Delete temp file
del "%vbsFile%"

echo Shortcut should now be in Startup folder
pause