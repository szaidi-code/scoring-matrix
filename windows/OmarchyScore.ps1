#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'reports'),
    [int]$TargetDiskNumber = -1,
    [string]$Label = $env:COMPUTERNAME,
    [string]$CompareDirectory,
    [ValidateSet('Unknown','Enabled','Disabled')]
    [string]$SecureBootReported = 'Unknown'
)
$ErrorActionPreference = 'Stop'
$version = '1.0'
if ($CompareDirectory) {
    $rows = @(Get-ChildItem -LiteralPath $CompareDirectory -Filter '*.json' | ForEach-Object {
        $r = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
        if ($r.MatrixVersion -ne $version) { throw "Incompatible matrix in $($_.Name)" }
        [pscustomobject]@{Computer=$r.Computer; Score=$r.Score; Resources=$r.Resources; Compatibility=$r.Compatibility; Coverage=$r.Coverage; Status=$r.Status; Captured=$r.Captured}
    })
    $rows | Sort-Object @{Expression='Score';Descending=$true} | Format-Table -AutoSize
    return
}
$issues = [Collections.Generic.List[string]]::new()
$parts = [Collections.Generic.List[object]]::new()
function Read-Hardware([string]$Name, [scriptblock]$Query) {
    try { & $Query } catch { $issues.Add("${Name}: $($_.Exception.Message)") }
}
function Add-Score([string]$Category,[int]$Points,[int]$Maximum,[bool]$Known,[string]$Reason) {
    $parts.Add([pscustomobject]@{Category=$Category;Points=$Points;Maximum=$Maximum;Known=$Known;Reason=$Reason})
}
function Tier([double]$Value, [array]$Thresholds, [array]$Points) {
    for($i=0;$i -lt $Thresholds.Count;$i++){ if($Value -ge $Thresholds[$i]){ return [int]$Points[$i] } }
    return 0
}
$system = Read-Hardware 'System' { Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory }
$cpu = @(Read-Hardware 'CPU' { Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,Architecture })
$os = Read-Hardware 'Memory availability' { Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory }
$memory = @(Read-Hardware 'Memory modules' { Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,Speed,ConfiguredClockSpeed,Manufacturer,PartNumber })
$disks = @(Read-Hardware 'Disks' { Get-Disk | Select-Object Number,FriendlyName,BusType,Size,AllocatedSize,PartitionStyle,IsBoot,IsSystem,HealthStatus,OperationalStatus })
$physical = @(Read-Hardware 'Disk media' { Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,MediaType,BusType,Size,HealthStatus })
$volumes = @(Read-Hardware 'Volumes' { Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter,FileSystem,Size,SizeRemaining,HealthStatus })
$gpu = @(Read-Hardware 'Graphics' { Get-CimInstance Win32_VideoController | Select-Object Name,PNPDeviceID,DriverVersion,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate })
$network = @(Read-Hardware 'Network' { Get-NetAdapter -Physical | Where-Object { $_.Status -ne 'Not Present' } | Select-Object InterfaceDescription,PhysicalMediaType,MediaType,Status,LinkSpeed,PnPDeviceID })
$devices = @(Read-Hardware 'Peripherals' { Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -in @('Bluetooth','MEDIA','Camera','Monitor','HIDClass') } | Select-Object Name,PNPClass,HardwareID,ConfigManagerErrorCode })
$battery = @(Read-Hardware 'Battery' { Get-CimInstance Win32_Battery | Select-Object Name,DesignCapacity,FullChargeCapacity,EstimatedChargeRemaining,BatteryStatus })
$firmware = Read-Hardware 'Firmware' { (Get-ComputerInfo -Property BiosFirmwareType).BiosFirmwareType.ToString() }
$secureBootSource = 'Detected'
if($SecureBootReported -ne 'Unknown'){
    $secureBoot = $SecureBootReported -eq 'Enabled'
    $secureBootSource = 'User reported'
}else{
    $secureBoot = Read-Hardware 'Secure Boot' {
        try { Confirm-SecureBootUEFI } catch {
            $value = (Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State' -Name UEFISecureBootEnabled).UEFISecureBootEnabled
            if($value -notin @(0,1)){ throw 'Secure Boot status unavailable' }
            $value -eq 1
        }
    }
    if($null -eq $secureBoot){ $secureBootSource='Unknown' }
}
$ramGiB = if($system){ [math]::Round($system.TotalPhysicalMemory / 1GB,1) }else{ 0 }
$cores = ($cpu | Measure-Object NumberOfCores -Sum).Sum
$threads = ($cpu | Measure-Object NumberOfLogicalProcessors -Sum).Sum
$cpuPoints = (Tier $cores @(16,12,8,6,4,2,1) @(20,18,16,13,10,5,2)) + (Tier $threads @(24,16,8,4) @(5,4,3,1))
Add-Score 'CPU' $cpuPoints 25 ($cpu.Count -gt 0) "$cores physical cores / $threads threads; capacity proxy, not a speed benchmark"
Add-Score 'RAM' (Tier $ramGiB @(63,31,15,7,3) @(25,23,18,10,3)) 25 ($null -ne $system) "$ramGiB GiB installed"
if($TargetDiskNumber -ge 0){
    $target = $disks | Where-Object Number -eq $TargetDiskNumber | Select-Object -First 1
    if(-not $target){ throw "Target disk $TargetDiskNumber was not found. No report written." }
}else{
    $target = $disks | Where-Object IsBoot | Select-Object -First 1
    if(-not $target){ $issues.Add('Boot disk could not be identified; choose -TargetDiskNumber explicitly.') }
}
$media = 'Unknown'
$storagePoints = 0
if($target){
    $match = @($physical | Where-Object { $_.DeviceId -eq [string]$target.Number -and $_.FriendlyName -eq $target.FriendlyName -and $_.Size -eq $target.Size })
    if($match.Count -eq 1){ $media = [string]$match[0].MediaType }
    $storagePoints = Tier ($target.Size/1GB) @(950,475,237,119,60) @(8,7,5,3,1)
    if([string]$target.BusType -eq 'NVMe'){ $storagePoints += 12; $media='NVMe' }
    elseif($media -eq 'SSD'){ $storagePoints += 9 }
    elseif($media -eq 'HDD'){ $storagePoints += 2 }
    else { $issues.Add('Target disk media type unknown; no media points awarded.') }
    if([string]$target.BusType -in @('USB','iSCSI','Virtual','File Backed Virtual')){ $issues.Add('Target disk is external, remote, or virtual; inspect suitability manually.') }
    if([string]$target.HealthStatus -ne 'Healthy'){ $issues.Add('Target disk health is not Healthy; investigate before installation.') }
}
Add-Score 'Storage' $storagePoints 20 ($null -ne $target -and $media -ne 'Unknown') "Selected disk $($target.Number): $($target.FriendlyName), $media; capacity assumes repurposing this disk"
$gpuNames = ($gpu.Name -join '; ')
$graphicsPoints = 0
if($gpu.Count){
    if($gpuNames -match 'NVIDIA'){ $graphicsPoints=8; $issues.Add('NVIDIA/hybrid graphics: verify exact GPU driver support, external displays, and suspend in Linux.') }
    elseif($gpuNames -match 'Intel|AMD|Radeon'){ $graphicsPoints=12 }
    else { $graphicsPoints=3 }
    $issues.Add('Graphics points are a vendor-level estimate. Acceleration and display behavior are untested; final 3 points reserved for Linux validation.')
}
Add-Score 'Graphics' $graphicsPoints 15 ($gpu.Count -gt 0) $gpuNames
$wifi = @($network | Where-Object { [string]$_.PhysicalMediaType -match '802.11|Wireless' -or $_.InterfaceDescription -match 'Wi-Fi|WiFi|Wireless|WLAN|802.11' })
$ethernet = @($network | Where-Object { [string]$_.PhysicalMediaType -eq '802.3' -or $_.InterfaceDescription -match 'Ethernet|GbE|2.5Gb|10Gb' })
$wifiPoints = 0
if($wifi.Count){ $wifiPoints=2; if(($wifi.PnPDeviceID -join ' ') -match 'VEN_8086' -or ($wifi.InterfaceDescription -join ' ') -match 'Intel'){ $wifiPoints=4 } }
$networkPoints = $wifiPoints
if($ethernet.Count){ $networkPoints += 4 }
Add-Score 'Network' $networkPoints 10 ($network.Count -gt 0) "Wi-Fi: $($wifi.InterfaceDescription -join '; '); Ethernet: $($ethernet.InterfaceDescription -join '; '); final 2 Wi-Fi points require Linux validation"
if($wifi.Count){ $issues.Add('Wi-Fi chipset detected in Windows; exact PCI/USB ID, Linux firmware, connectivity, and Bluetooth coexistence still need validation.') }
elseif($network.Count){ $issues.Add('No Wi-Fi adapter detected. A disabled or hidden device may be missed.') }
$bootPoints=0
if($firmware -eq 'Uefi'){ $bootPoints=3; if($secureBoot -eq $false){ $bootPoints=5 } }
Add-Score 'Firmware' $bootPoints 5 ($null -ne $firmware -and $null -ne $secureBoot) "Firmware=$firmware; Secure Boot=$secureBoot ($secureBootSource)"
if($secureBoot -eq $true){ $issues.Add('Secure Boot is enabled; review Omarchy installation instructions. This script changes no firmware settings.') }
$status='Provisional - Linux validation required'
if(@($cpu | Where-Object Architecture -ne 9).Count){ $status='Not a standard x86-64 installation candidate' }
if(-not $cpu.Count -or -not $system -or -not $target){ $status='Incomplete inventory - do not rank yet' }
if($ramGiB -gt 0 -and $ramGiB -lt 7){ $issues.Add('Below the recommended 8 GB RAM class in this matrix (not an official minimum).') }
$score = ($parts | Measure-Object Points -Sum).Sum
$resources = ($parts | Where-Object Category -in @('CPU','RAM','Storage') | Measure-Object Points -Sum).Sum
$coverage = ($parts | Where-Object Known | Measure-Object Maximum -Sum).Sum
$report = [ordered]@{
    MatrixVersion=$version;Computer=$Label;Captured=(Get-Date).ToUniversalTime().ToString('o');SecureBootSource=$secureBootSource
    Score=$score;Resources=$resources;Compatibility=($score-$resources);Coverage=$coverage;Status=$status
    Breakdown=@($parts.ToArray());Issues=@($issues.ToArray())
    Inventory=[ordered]@{System=$system;CPU=$cpu;RAMGiB=$ramGiB;CurrentlyFreeRAMGiB=$(if($os){[math]::Round($os.FreePhysicalMemory/1MB,1)}else{$null});MemoryModules=$memory;Disks=$disks;PhysicalDisks=$physical;SelectedDisk=$target;Volumes=$volumes;Graphics=$gpu;Network=$network;Peripherals=$devices;Battery=$battery;Firmware=$firmware;SecureBoot=$secureBoot}
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$safeLabel = $Label -replace '[^a-zA-Z0-9_.-]','_'
$base = Join-Path $OutputDirectory ("{0}-{1}" -f $safeLabel,(Get-Date -Format 'yyyyMMdd-HHmmss'))
$report | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath "$base.json" -Encoding UTF8
$lines = @("OMARCHY SCORE: $score / 100", "Computer: $Label", "Resources: $resources / 70; compatibility estimate: $($score-$resources) / 30", "Inventory coverage: $coverage / 100 (not compatibility confidence)", "Status: $status", '', ($parts | Format-Table Category,Points,Maximum,Reason -Wrap | Out-String -Width 180), 'NOTES', ($issues -join "`r`n"), '', 'INVENTORY', ($report.Inventory | ConvertTo-Json -Depth 8))
$lines | Set-Content -LiteralPath "$base.txt" -Encoding UTF8
$lines[0..8] | Write-Output
Write-Output "Reports: $base.json and $base.txt"
