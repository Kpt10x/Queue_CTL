Write-Host "== QueueCTL Demo Starting ==" -ForegroundColor Cyan

Write-Host "`n[1] Enqueue success job" -ForegroundColor Yellow
python queuectl.py enqueue --file job_ok.json
Start-Sleep -Seconds 1

Write-Host "`n[2] Enqueue failure job" -ForegroundColor Yellow
python queuectl.py enqueue --file job_fail.json
Start-Sleep -Seconds 1

Write-Host "`n[3] Process success job with --once" -ForegroundColor Yellow
python queuectl.py worker start --once
Start-Sleep -Seconds 1

Write-Host "`n[4] Begin processing failing job (this part waits for retries...)" -ForegroundColor Yellow

# Launch worker process
$job = Start-Process -FilePath "python" -ArgumentList "queuectl.py", "worker", "start" -PassThru

# Let it run long enough to hit retries → DLQ
Start-Sleep -Seconds 18

# Simulate Ctrl + C
Stop-Process -Id $job.Id -Force
Write-Host "Worker stopped (simulated Ctrl+C)."

Start-Sleep -Seconds 2

Write-Host "`n[5] Show status" -ForegroundColor Yellow
python queuectl.py status
Start-Sleep -Seconds 1

Write-Host "`n[6] Show DLQ list" -ForegroundColor Yellow
python queuectl.py dlq list
Start-Sleep -Seconds 1

Write-Host "`n[7] Retry DLQ job: job_fail" -ForegroundColor Yellow
python queuectl.py dlq retry job_fail
Start-Sleep -Seconds 1

Write-Host "`n[8] Process DLQ job again with --once" -ForegroundColor Yellow
python queuectl.py worker start --once
Start-Sleep -Seconds 1

Write-Host "`n[9] Show final job list" -ForegroundColor Yellow
python queuectl.py list

Write-Host "`n== Demo Complete ==" -ForegroundColor Green
