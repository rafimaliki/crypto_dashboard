## MLFlow
### Dashboard
```bash
# cmd untuk membuka dashboard MLFlow di browser

# 1. Jika menjalankan di lokal
http://localhost:5000

# 2. Jika menjalankan di server, dan ingin buka dashboard melalui SSH
ssh -L 5000:localhost:5000 xops@rafif.me -p 2222
# lalu buka http://localhost:5000 di browser lokal 
```

## ml-train
### /retrain
```bash
# Untuk run retrain, kirim POST atau curl sebagai berikut:
curl -X POST http://localhost:8001/retrain \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "scheduled_weekly_retrain",
    "called_by": "n8n_workflow"
  }'
```
* Retrain akan menjalankan ulang training dan menghasilkan model baru, tapi **model baru belum tentu menggantikan model sekarang**. Model hanya dipromosi jika acc > acc model saat ini.

## ml-predict
### /predict
```bash
# Untuk mendapatkan prediksi Buy / Sell / Hold
curl -X POST localhost:8000/predict
```

### /metrics
```bash
# Untuk mendapatkan akurasi model saat ini
curl -X GET http://localhost:8000/metrics
```