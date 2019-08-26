#!/usr/bin/python
import os, inspect, datetime
from ConfigParser import ConfigParser
import psycopg2
 
 
def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)
 
    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
 
    return db

def connect():
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = config()
 
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)
 
        # create a cursor
        cur = conn.cursor()
        
 # execute a statement
        print('PostgreSQL database version:')
        cur.execute('SELECT version()')

        # display the PostgreSQL database server version
        db_version = cur.fetchone()
        print(db_version)
        return conn

     # close the communication with the PostgreSQL
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    # finally:
    #     if conn is not None:
    #         conn.close()
    #         print('Database connection closed.')
 

def ex_import_padron():

    conn = connect()
    cur = conn.cursor()
    content = str()
    try:
        fp = open('./padron.txt', 'r')
        content = fp.readlines()
    except:
        print "error abriendo archivo"


    content = [x.strip() for x in content]
    for i,line in enumerate(content):
        l = line.split(';')
        if i % 10000 == 0:
            print "ya importado " + str(i) + " lineas " + str(datetime.datetime.now())

        SQL = """
                SELECT id FROM ret_padron WHERE issue_date=%(date)s AND main_id_number=%(str)s
        """
        data = {'str':l[3],'date':str(datetime.datetime.strptime(l[0],'%d%m%Y').date())}
        cur.execute(SQL,data)
        id = cur.fetchone()
        if not id:
            vals = {'main_id_number':l[3],
                    'issue_date':str(datetime.datetime.strptime(l[0], '%d%m%Y').date()),
                    'sdate':str(datetime.datetime.strptime(l[1], '%d%m%Y').date()),
                    'edate':str(datetime.datetime.strptime(l[2], '%d%m%Y').date()),
                    'type':l[4],
                    'percep_rate':l[7].replace(',', '.'),
                    'whold_rate':l[8].replace(',', '.'),
                    'percep_group':l[9],
                    'whold_group':l[10]
                    }
            SQL = "INSERT INTO ret_padron (%s) VALUES (%s) RETURNING id;" % (
                ",".join(vals),
                ",".join("%%(%s)s" % name for name in vals),
            )
            cur.execute(SQL, vals)
            conn.commit()

    try:
        fp.close()
        conn.close()
    except:
        pass


ex_import_padron()