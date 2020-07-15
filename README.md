# aria2cli
aria2cli is a aria2 rpc client in CLI

## Install dependencies
```bash
pip install requests, fire
```

## Config
Set your `host` `port` `token` in aria2cli.py

## Usage
- list task
    - list all task
        ```bash
        python aria2cli.py
        python aria2cli.py list
        python aria2cli.py list all
        ```

    - list all task (show task gid)
        ```bash
        python aria2cli.py list --format=detail
        ```

    - list active task
        ```bash
        python aria2cli.py list active
        ```

    - list stopped/finshed task
        ```bash
        python aria2cli.py list stopped
        ```


- new task
    ```bash
    python aria2cli.py new URL
    ```

- show task infomation
    ```bash
    python aria2cli.py show TASK_GID
    ```

- pause and unpause task
    ```bash
    python aria2cli.py pause TASK_GID
    python aria2cli.py unpause TASK_GID
    ```

- purge all stopped/finshed task
    ```bash
    python aria2cli.py purge
    ```

- remove a task
    ```bash
    python aria2cli.py remove TASK_GID
    ```