# 🚀 Act Usage Guide for Windows PowerShell

## ✅ **Act is Successfully Installed!**

**Version**: 0.2.80  
**Location**: `C:\Users\[USERNAME]\AppData\Local\Microsoft\WinGet\Packages\nektos.act_Microsoft.Winget.Source_8wekyb3d8bbwe\act.exe`

## 🔧 **Setup (One-time)**

The Act alias has been added to your PowerShell profile. It will be available in all new PowerShell sessions.

## 🧪 **Testing Workflows**

### **Prerequisites**
1. **Docker Desktop**: Must be running
2. **PowerShell**: Use PowerShell (not Command Prompt)

### **Basic Commands**

```powershell
# Check Act version
act --version

# Test comprehensive tests workflow (PR validation)
act pull_request -W .github/workflows/test-comprehensive.yml --dryrun

# Test frontend tests workflow
act pull_request -W .github/workflows/test-frontend.yml --dryrun

# Test production build workflow
act push -W .github/workflows/build-publish-release.yml --dryrun

# Test development build workflow
act push -W .github/workflows/build-dev.yml --dryrun

# Test production build workflow
act push -W .github/workflows/build-publish-release.yml --dryrun

# Test documentation build workflow
act pull_request -W .github/workflows/build-docs.yml --dryrun
```

### **Run Actual Tests (Remove --dryrun)**

```powershell
# Run comprehensive tests (this will take time)
act pull_request -W .github/workflows/test-comprehensive.yml

# Run frontend tests
act pull_request -W .github/workflows/test-frontend.yml

# Run production build (this will take longer)
act push -W .github/workflows/build-publish-release.yml

# Run development build
act push -W .github/workflows/build-dev.yml
```

## 🎯 **What Each Workflow Tests**

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `test-comprehensive.yml` | All tests (Carla + Web + Frontend) | PR validation |
| `test-frontend.yml` | Frontend tests only | PR with frontend changes |
| `build-publish-release.yml` | Production build + release | Push to master |
| `build-dev.yml` | Development build | Push to develop |
| `build-docs.yml` | Documentation build | PR with docs changes |

## ⚠️ **Common Issues**

### **Wrong Event Type**
```
Error: Could not find any stages to run. View the valid jobs with `act --list`.
```
**Solution**: Use the correct event type:
- `build-dev.yml` and `build-publish-release.yml` → Use `act push`
- `test-comprehensive.yml`, `test-frontend.yml`, `build-docs.yml` → Use `act pull_request`

### **Docker Not Running**
```
Error: error during connect: in the default daemon configuration on Windows, the docker client must be run with elevated privileges
```
**Solution**: Start Docker Desktop

### **Act Not Found**
```
act : The term 'act' is not recognized
```
**Solution**: 
```powershell
# Set alias manually
Set-Alias -Name act -Value "C:\Users\$env:USERNAME\AppData\Local\Microsoft\WinGet\Packages\nektos.act_Microsoft.Winget.Source_8wekyb3d8bbwe\act.exe"
```

### **First Run Slow**
The first run downloads Docker images (~500MB). Subsequent runs will be faster.

## 🎉 **Success Indicators**

When workflows run successfully, you'll see:
- ✅ Green checkmarks for passed jobs
- 📊 Test results and coverage reports
- 🐳 Docker containers starting and stopping
- 📦 Artifacts being created

## 💡 **Tips**

1. **Use `--dryrun` first** to validate workflow syntax
2. **Start with simple workflows** like `test-frontend.yml`
3. **Check Docker Desktop** is running before testing
4. **Monitor system resources** - Act uses Docker containers
5. **Use PowerShell** - Act works best with PowerShell on Windows

## 🔄 **Workflow Testing Flow**

```
1. Edit workflow file
2. Test with --dryrun
3. Fix any syntax issues
4. Run without --dryrun
5. Check results
6. Push to GitHub if successful
```

## 📝 **Example Session**

```powershell
# Test workflow syntax
act pull_request -W .github/workflows/test-comprehensive.yml --dryrun

# If successful, run actual tests
act pull_request -W .github/workflows/test-comprehensive.yml

# Check results in terminal output
# Look for ✅ PASSED indicators
```

---

**Happy Testing! 🎉**
