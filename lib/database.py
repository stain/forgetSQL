"""Database transparancy package.

Convenient functions:
  cursor() -- 
    Returns a cursor from an active connection. If the connection has
    timed out, a new one is created in place. Normally you would
    use cursor()-objects to avoid filling up the database with
    too many connections.
    Depending on the DB implementation, the cursor objects
    might or might not be thread safe.
  connect() --
    Gives a seperatte DB connection using the configfile specified parameters.
"""

import config

def _getDefaultParams():
  params = {}
  for option in config.conf.options("database"):
    # Everything inside [database] except module
    # goes directly to the module.connect
    if option.lower() == 'module':
      continue 
## This won't work with MySQLdb - which want's a dictionary      
#    params.append("%s=%s" % 
#         (option, config.conf.get('database', option)))
#  return " ".join(params) # ie "hostname=blapp username=knott"       
    params[option] = config.conf.get('database', option)
  return params

def connect(params=None):
  """Returns a database connection"""
  dbmodule = __import__(config.conf.get('database', 'module'))

  if params is None:
    params = _getDefaultParams() # Default ones

  # Will most certainly fail if parameters are wrong.
  # This is intended.
  if type(params) != type({}):
      return dbmodule.connect(params)
  else:    
      return dbmodule.connect(**params)

class ConnectionHolder:
  def __init__(self, connection=None):
    self.connection = connection
    self.cursors = 0
  def cursor(self):
    if(self.connection is None):
      # First time! It must be exciting for ya!
      self.connection = connect()
      # self.connection.autocommit(1)
    try:
      cursor = self.connection.cursor()
    except:
      # We might have disconnected. Get a new one!
      # (the old one will live on for a while in
      #  active cursor, they might fail as well)
      self.connection = connect()
      cursor = self.connection.cursor()
    self.cursors += 1  # Just some statistics  
    return cursor  

_connectionHolder = ConnectionHolder()

# Exports the cursor method
cursor = _connectionHolder.cursor

