@echo off
REM Script to create and push to a new branch for the model repository fix

REM Branch name with date for uniqueness
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set BRANCH_NAME=fix/model-repository-%datetime:~0,8%

echo Creating new branch: %BRANCH_NAME%
git checkout -b %BRANCH_NAME%

echo Adding modified files...
git add .
echo Committing changes...
git commit -m "Fix model repository serialization and update documentation

- Fix NumPy array serialization in FileModelRepository
- Update interface to use explicit FLModel type
- Add proper model versioning with metadata
- Create cleanup tool for legacy model formats
- Update documentation to reflect new model storage format"

echo Pushing to remote repository...
git push origin %BRANCH_NAME%

echo Done! New branch '%BRANCH_NAME%' has been pushed to the remote repository.
echo To create a pull request, visit your Git repository web interface.
pause 