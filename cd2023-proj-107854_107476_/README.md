# CD 2023 Project


## Setup

Run the following commands to execute the project properly:

RabbitMQ Stuff
```bash
rabbitmqctl add_vhost broker
rabbitmqctl set_permissions -p broker guest ".*" ".*" ".*"
```

General Stuff
```bash
source venv/bin/activate

python server.py
python worker.py #(multiple executions if u wish)
```

## Authors

* **Rafael Vilaça** - [Rafa548](https://github.com/Rafa548)
* **Vitalie Bologa** - [Vitalie03](https://github.com/Vitalie03)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.