Add-Type -AssemblyName PresentationFramework

$NAME = "TwitchNotifierWin"
$FILE = ".\twitchnotify_win.py"
$FILE_VER = "0.1"

echo "Installing $NAME"
echo "Argument: $args[0]"

function Show-Message
{
    param([System.String] $title, [System.String] $msg)
    [System.Windows.MessageBox]::Show($msg, $title)
}

function Prompt-YesNo
{
    param([System.String] $title, [System.String] $msg)
    return [System.Windows.MessageBox]::Show($msg, $title, "YesNo", "Question")
}

function Get-Python([System.String]$name)
{
    $python = Get-Command -Name $name
    if (-not $?)
    {
        return $null
    }
    return $python
}

function Get-Version
{
    param($obj)
    $version = & $obj --version 2>&1
    if ($version -eq $null)
    {
        return $null
    }
    $version = $version | Select-String -Pattern "Python ([0-9\.]+)" -AllMatches
    return $version.Matches[0].Value
}

# User provided runtime
if ($args[0] -ne $null)
{
    $pythonver = Get-Version $args[0]
    if ($pythonver -eq $null)
    {
        Show-Message -title "Error" -msg "Given path was not valid Python3 runtime"
        exit 1
    }
    $python = True
}

# Get Python version automatically
if ($python -eq $null)
{
    $python = Get-Python("python3")
}
if ($python -eq $null)
{
    $python = Get-Python("python")
}

if ($python -eq $null)
{
    Show-Message -title "Failed" -msg "No Python 3 installation was found"
    exit 1
}


# Check Python version
$pythonver = Get-Version -obj $python
if ($pythonver -match "Python 2")
{
    Show-Message -title "Failed" -msg "The Python version you have in PATH is Python 2!`n Python 3 is a requirement."
    exit 1
}

if ($pythonver -notmatch "Python 3")
{
    Show-Message -title "Failed" -msg "The Python version you have in PATH is is unkown."
    exit 1
}

$confirm = Prompt-YesNo -title "$NAME installation" -msg "Installing $NAME as a Windows service`n`nUsing Python runtime at $($python.Path)`n`nIs this OK?"

if ($confirm -eq "No")
{
    echo "Exiting"
}

$fullpath = (Get-Item -Path $FILE).FullName
if (-not $?)
{
    Show-Message -title "Error" -msg "Main python script was not found"
}
$command = "$($python.Path) -- $fullpath"
New-Service -Name $NAME -Description "Shows toasts when Twitch stream becomes live" -BinaryPathName $command -DisplayName "Twitch Notifier $FILE_VER"

Start-Sleep -Seconds 3
Get-Service -Name $NAME

if ($?)
{
    Show-Message -title "Success" -msg "Service has been installed"
}
else
{
    Show-Message -title "Failure" -msg "Something went wrong and service was not installed"
}