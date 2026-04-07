# PowerShell launcher for BetterCopilot GUI using Python 3.14
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    $args
)

$python = 'C:\Users\surfing\AppData\Local\Programs\Python\Python314\python.exe'
$script = Join-Path $PSScriptRoot 'run_gui.py'
& $python $script @args
