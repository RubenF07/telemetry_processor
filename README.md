# Env Setup (Windows)
^ serial reading didn't work on WSL :(

### Create Venv:
```
py -m venv venv
```

### Start Venv (PowerShell):
```
.\venv\Scripts\Activate.ps1
```

### Intall Reqs:
```
python -m pip install -r requirements.txt
```


### Exit Venv:
```
deactivate
```


# Database setup (On WSL)

### Start Grafana
```
sudo systemctl daemon-reload
sudo systemctl start grafana-server
```

### Open Grafana
[localhost:3000](localhost:3000)

### Initialize influx with telegraf
[Influx](https://docs.influxdata.com/influxdb3/enterprise/install/)
[Telegraf](https://docs.influxdata.com/telegraf/v1/get-started/)

### Start telegraf
```
sudo systemctl start telegraf
```

### Start influx DB(with GUI)
```
influxdb3 serve --mode all,webui   --webui-session-secret local-dev-only   --without-auth  --node-id host01   --cluster-id cluster01   --object-store file   --data-dir ~/.influxdb3
```

### Open influx GUI
[localhost:8181](localhost:8181)


# Forward with Ngrok:
```
ngrok http 3000 --url https://chaffing-subdued-feline.ngrok-free.dev
```
(This is just one of my ngrok domains)