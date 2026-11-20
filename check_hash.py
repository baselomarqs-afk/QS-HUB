import getpass
import os
import bcrypt
import pymysql
from utils.settings import DbSettings

password = os.environ.get("QTO_ADMIN_PASSWORD") or getpass.getpass("Password to verify: ")
conn = pymysql.connect(**DbSettings.from_env().pymysql_kwargs())
c = conn.cursor()

c.execute("SELECT email, password_hash FROM qto_users WHERE email='basel00omar.92@gmail.com'")
res = c.fetchone()
print(res)

print('Is match?', bcrypt.checkpw(password.encode('utf-8'), res['password_hash'].encode('utf-8')))
