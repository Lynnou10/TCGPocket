rmdir /s /q "./build"
rmdir /s /q "./dist"
del "./PTCGTracker.spec"
pyinstaller --onefile --icon=favicon.ico -n PTCGTracker server.py
xcopy cards dist\cards /s /i
xcopy utils dist\utils /s /i
xcopy favicon.ico dist\favicon.ico*
xcopy index.html dist\index.html*
xcopy styles.css dist\styles.css*
rmdir /s /q "./build"
del "./PTCGTracker.spec"

pause