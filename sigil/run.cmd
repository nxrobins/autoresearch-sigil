@echo off
REM Usage: run.cmd [seed] [generations]   (defaults 42 12)
set SIGIL=D:\SIGIL\target\x86_64-pc-windows-gnu\debug\sigil.exe
set SEED=%1
set GENS=%2
if "%SEED%"=="" set SEED=42
if "%GENS%"=="" set GENS=12
"%SIGIL%" forge "%~dp0autoresearch.sigil" --input "%SEED% %GENS%" --fuel 400000000
