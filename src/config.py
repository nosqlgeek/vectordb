import os

CONFIG = {
    "db_host" : os.getenv("DB_HOST"),
    "db_port" : os.getenv("DB_PORT"),
    "db_password" : os.getenv("DB_PASSWORD")
}