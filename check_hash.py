import utils.db, pymysql, bcrypt
from utils.settings import DbSettings

conn = pymysql.connect(**DbSettings.from_env().pymysql_kwargs())
c = conn.cursor()

c.execute("SELECT email, password_hash FROM qto_users WHERE email='basel00omar.92@gmail.com'")
res = c.fetchone()
print(res)

print('Is match?', bcrypt.checkpw(b'Nodnod1606', res['password_hash'].encode('utf-8')))
