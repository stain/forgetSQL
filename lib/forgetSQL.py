#!/usr/bin/env python


## Distributed under LGPL
## (c) Stian Søiland 2002-2003
## stian@soiland.no
## http://forgetsql.sourceforge.net/

## $Log$
## Revision 1.6  2003/07/11 12:34:01  stain
## _sqlSequence defines the name of a tables sequence for
## _getNextSequence.
##
## _getNextSequence includes _ after tablename, so the result is
## table_column_seq, not tablecolumn_seq.
##
## The constructor of forgetters supports multiple values as multiple
## parameters, not a tupple anymore. _getID() returns a tupple when
## appropriate, as always, so myClass(self.reference._getID()) should
## work...
##

import exceptions, time, re, types, pprint, sys

# from nav import database

try:
    from mx import DateTime
except:
    DateTime = None

try:
  True,False
except NameError:
  raise "True/False needed, too old Python?"

class NotFound(exceptions.Exception):
  pass

class Forgetter:
  """SQL to object database wrapper.
  Given a welldefined database, by subclassing Forgetter
  and supplying some attributes, you may wrap your SQL tables
  into objects that are easier to program with. 

  You must define all fields in the database table that you want
  to expose, and you may refine the names to suit your
  object oriented programming style. (ie. customerID -> customer)

  Objects will be created without loading from database, 
  loading will occur when you try to read or write some of the
  attributes defined as a SQL field. If you change some attributes the
  object will be saved to the database by save() or garbage
  collection. (be aware that GC in Py >= 2.2 is not immediate)

  If you want to create new objects, just supply them with blank
  ID-fields, and _nextSequence() will be called to fetch a new
  ID used for insertion.

  The rule is one class pr. table, although it is possible
  to join several table into one class, as long as the 
  identificator is unique. 

  By defining _userClasses you can resolve links to other
  tables, a field in this table would be an id in another
  table, ie. another class. In practical use this means that
  behind attributes pointing to other classes (tables)
  you will find instances of that class.

  Short example usage of forgetterobjects:
  
  # Process all
  for user in User.getAllIterator():
    print user.name
    print "Employed at:"
    print user.employed.name, user.employed.address
    user.employed = None # fire him
  
  # Retrieve some ID
  shop = Shop(552)
  shop.name = 'Corrected name'
  shop.save()   # Not neccessary, called at garbage collection
  
  # Include SQL where statements in selections
  myIDs = User.getAllIDs(("name='soiland'", 'salary > 5'))
  

  Requirements: A module named 'database' exporting the method
                cursor(), which should obviously return a cursor.
                The cursor should be DB 2.0 complient, preferably
                with autocommit turned on. (Transactions are not
                within the scope of this module yet)

                Python 2.2 (iterators, methodclasses)
  """
  # Will be 1 once prepare() is called
  _prepared = 0

  # The default table containing our fields
  # _sqlTable = 'shop'
  _sqlTable = ''

  # A mapping between our fields and the database fields.
  # 
  # You must include all fields needed here. You may specify 
  # other names if you want to make the sql name more approriate
  # for object oriented programming. (Like calling a field 'location' 
  # instead of 'location_id', because we wrap the location in a seperate
  # object and don't really care about the id)
  # 
  # You may reference to other tables with a dot, all
  # other db fields will be related to _sqlTable.
  # If you reference other tables, don't forget to
  # modify _sqlLinks.
  # 
  # Note that 'id' field MUST be defined unless
  # _sqlPrimary is redefined.
  # 
  #  _sqlFields = {
  #    'id':   'shop_id',
  #    'name': 'name',
  #    'location': 'location_id',
  #    'chain': 'shop_chain_id',
  #    'address': 'address.address_id',
  #  }
  _sqlFields = {}

  # A list of attribute names (in the object, not database)
  # that are the primary key in the database. Normally
  # 'id' is sufficient. It is legal to have 
  # multiple fields as primary key, but it won't work
  # properly with _userClasses and getChildren().
  _sqlPrimary = ('id',)
  
  # When using several tables, you should include a
  # 'link' statement, displaying which fields link the
  # two tables together. Note that these are sql names.
  #  _sqlLinks = (
  #    ('shop_id', 'address.shop_id'),
  #  )
  _sqlLinks = ()

  # The name of the sequence used by _nextSequence
  # - if None, a guess will be made based on _sqlTable
  # and _sqlPrimary.
  _sqlSequence = None

  # Order by this attribute by default, if specified
  # _orderBy = 'name' - this could also be a tupple
  _orderBy = None

  # _userClasses can be used to trigger creation of a field 
  # with an instance of the class. The given database field
  # will be sent to the constructor as an objectID
  # (ie. as self.id in this object) (ie. the class does not
  # neccessary need to be a subclass of Forgetter)
  #
  # This means that the attribute will be an instance of that
  # class, not the ID. The object will not be loaded from the
  # database until you try to read any of it's attributes, 
  # though. (to prevent unneccessary database overload and
  # recursions)
  # 
  # Notice that _userClasses must be a name resolvable, ie. 
  # from the same module as your other classes.
  #  _userClasses = {
  #    'location': 'Location',
  #    'chain': 'Chain',
  #    'address': 'Address',
  #  }
  _userClasses = {}

  # If you want userClasses to work properly with strings instead of
  # instances, you must also 'prepare' your classes to resolve the
  # names.  This must be done from the same module you are defining the
  # classes: forgetSQL.prepareClasses(locals())

  # A list of fields that are suitable for a textual 
  # representation (typical a one liner). 
  # 
  # Fields will be joint together with spaces or
  # simular.
  # _shortView = ('name')
  _shortView = ()
 
  # Description for the fields (ie. labels)
  # Note that these fields will be translated with the _ function.
  # If a field is undescribe, a capitalized version of the field name
  # will be presented.
  #_descriptions = {
  #  'name': 'Full name',
  #  'description': 'Description of thingie',
  #}
  _descriptions = {}

  def cursor(cls):
    try:
      import database
      return database.cursor()
    except:  
      raise "cursor method undefined, no database connection could be made"
  cursor = classmethod(cursor)  

  # a reference to the database module used, ie. 
  # MySQLdb, psycopg etc.
  _dbModule = None
 
  def __init__(self, *id):
    """Initialize, possibly with a database id. 
    Note that the object will not be loaded before you call load()."""
    self._values = {}
    self.reset()
    if not id:
      self._resetID()
    else:  
      self._setID(id)
  def _setID(self, id):
    """Sets the ID, id can be either a list, following the
       _sqlPrimary, or some other type, that will be set
       as the singleton ID (requires 1-length sqlPrimary).
       
       Note that this means you cannot have tuples as
       primary keys directly into the database unless you
       double pack then, ie dirty one:
         _setID(((1,2),))
       (I don't think anyone want's tupple fields in their database
       as a primary key, though)
       """
    if type(id) in (types.ListType, types.TupleType):
      try:
        for key in self._sqlPrimary:
          value = id[0]
          self.__dict__[key] = value
          id = id[1:] # rest, go revursive
      except IndexError:
        raise 'Not enough id fields, required: %s' % len(self._sqlPrimary)
    elif len(self._sqlPrimary) <= 1:
      # It's a simple value
      key = self._sqlPrimary[0]
      self.__dict__[key] = id
    else:
      raise 'Not enough id fields, required: %s' % len(self._sqlPrimary)
    self._new = False  
      
  def _getID(self):
    """Gets the ID values as a tupple annotated by sqlPrimary"""
    id = []
    for key in self._sqlPrimary:
      value = self.__dict__[key]
      if isinstance(value, Forgetter):
        # It's another object, we store only the ID
        if value._new:
          # It's a new object too, it must be saved!
          value.save()
        try:
          (value,) = value._getID()
        except:
          raise "Unsupported: Part %s of %s primary key is a reference to %s, with multiple-primary-key %s " % (key, self.__class__, value.__class__, value)
      id.append(value)
    return id

  def _resetID(self):  
    """Resets all ID fields."""
    # Dirty.. .=))
    self._setID((None,) * len(self._sqlPrimary))
    self._new = True

  def _validID(self):
    """Is all ID fields with values, ie. not None?"""
    return not None in self._getID()
  
  def __getattr__(self, key):
    """Will be called when an unknown key is to be
       retrieved, ie. most likely one of our database
       fields."""
    if self._sqlFields.has_key(key):
      if not self._updated:
        self.load()
      return self._values[key]
    else:
      raise AttributeError, key
      
  def __setattr__(self, key, value):
    """Will be called whenever something needs to be set, so
       we store the value as a SQL-thingie unless the key
       is not listed in sqlFields."""
    if key not in self._sqlPrimary and self._sqlFields.has_key(key):
      if not self._updated:
        self.load()
      self._values[key] = value
      self._changed = time.time()
    else:
      # It's a normal thingie
      self.__dict__[key] = value
  
  def __del__(self):
    """Saves the object on deletion. Be aware of this. If
       you want to undo some change, use reset() first.
       
       Be aware of Python 2.2's garbage collector, that
       might run in the background. This means that
       unless you call save() changes might not
       be done immediately in the database.

       Not calling save() also means that you cannot catch
       errors caused by wrong insertion/update (ie. wrong
       datatype for a field)
       """
    try:
      self.save()
    except Exception, e:
      pass
  
  def _checkTable(cls, field):
    """Splits a field from _sqlFields into table, column.
       Registers the table in cls._tables, and returns
       a fully qualified table.column 
       (default table: cls._sqlTable)"""
    # Get table part
    try:
      (table, field) = field.split('.')
    except ValueError:
      table = cls._sqlTable
    # clean away white space 
    table = table.strip()
    field = field.strip()
    # register table
    cls._tables[table] = None
    # and return in proper shape
    return table + '.' + field

  _checkTable = classmethod(_checkTable)  

  def reset(self):
    """Reset all fields, almost like creating a new object.
    Note: Forgets changes you have made not saved to database!
    (Remember: Others might reference the object already, 
    expecting something else!)
    Override this method if you add properties
    not defined in _sqlFields"""
    self._resetID()
    self._updated = None
    self._changed = None
    self._values = {}
    # initially create fields
    for field in self._sqlFields.keys():
      self._values[field] = None

  def load(self, id=None):
    """Loads from database if neccessary."""
    if not id is None:
      self.reset()
      self._setID(id)
    if not self._new and self._validID():  
      self._loadDB()
    self._updated = time.time()
  
  def save(self):
    if (self._validID() and self._changed) or (self._updated and self._changed > self._updated):
      # Don't save if we have not loaded existing data!
      self._saveDB()

  def delete(self):
    """Marks this object for deletion in the database. 
       The object will then be reset and ready for use 
       again with a new id."""
    (sql, ) = self._prepareSQL("DELETE")
    curs = self.cursor()
    curs.execute(sql, self._getID())
    curs.close()
    self.reset()
    
  def _prepareSQL(cls, operation="SELECT", where=None, selectfields=None, orderBy=None):
    """Returns a sql for the given operation.
       Possible operations:
         SELECT     read data for this id
         SELECTALL  read data for all ids
         INSERT     insert data, create new id
         UPDATE     update data for this id
         DELETE     remove data for this id
         
       SQL will be built by data from _sqlFields, and will
       contain 0 or several %s for you to sprintf-format in later:

         SELECT --> len(cls._sqlPrimary)
         SELECTALL --> 0 %s
         INSERT --> len(cls._sqlFields) %s (including id)  
         UPDATE --> len(cls._sqlFields) %s (including id)
         DELETE --> len(cls._sqlPrimary)

       (Note: INSERT and UPDATE will only change values in _sqlTable, so
        the actual number of fields for substitutions might be lower
        than len(cls._sqlFields) )

       For INSERT you should use cls._nextSequence() to retrieve
       a new 'id' number. Note that if your sequences are not named
       tablename_primarykey_seq  (ie. for table 'blapp' with primary key
       'john_id', sequence name blapp_john_id_seq) you must give the sequence
       name as an optional argument to _nextSequence)

       Additional note: cls._nextSequence() MUST be overloaded
       for multi _sqlPrimary classes. Return a tupple.
       
       Return values will always be tuples:
         SELECT --> (sql, fields)
         SELECTALL -> sql, fields)
         INSERT -> (sql, fields)
         UPDATE -> (sql, fields)
         DELETE -> (sql,)  -- for consistency
       
       fields will be object properties as a list, ie. the keys from
       cls._sqlFields. The purpose of this list is to give the programmer
       an idea of which order the keys are inserted in the SQL, giving
       help for retreiving (SELECT, SELECTALL) or inserting for %s
       (INSERT, DELETE).

       Why? Well, the keys are stored in a hash, and we cannot be sure
       about the order of hash.keys() from time to time, not even with
       the same instance.

       Optional where-parameter applies to SELECT, SELECTALL and DELETE.
       where should be a list or string of where clauses.
       
      """   
    # Normalize parameter for later comparissions
    operation = operation.upper()
    # Convert where to a list if it is a string
    if type(where) in (types.StringType, types.UnicodeType):
      where = (where,)
    if orderBy is None:
      orderBy = cls._orderBy  
    
    if operation in ('SELECT', 'SELECTALL'):
      # Get the object fields and sql fields in the same
      # order to be able to reconstruct later.
      fields = []
      sqlfields = []
      for (field, sqlfield) in cls._sqlFields.items():
        if selectfields is None or field in selectfields:
            fields.append(field)
            sqlfields.append(sqlfield)
      if not fields:
        # dirrrrrty!
        raise """ERROR: No fields defined, cannot create SQL. 
Maybe sqlPrimary is invalid?
Fields asked: %s
My fields: %s""" % (selectfields, cls._sqlFields)
        
      sql = "SELECT\n  "
      sql += ', '.join(sqlfields)  
      sql += "\nFROM\n  "
      tables = cls._tables.keys()
      if not tables:
        raise "REALITY ERROR: No tables defined"
      sql += ', '.join(tables)
      tempWhere = ["%s=%s" % linkPair for linkPair in cls._sqlLinks]
      # this MUST be here.
      if operation <> 'SELECTALL':
        for key in cls._sqlPrimary:
          tempWhere.append(cls._sqlFields[key] + "=%s")
      if where:
        tempWhere += where
      if(tempWhere):
        sql += "\nWHERE\n  "
        sql += ' AND\n  '.join(tempWhere) 
      if operation == 'SELECTALL' and orderBy:
        sql += '\nORDER BY\n  '
        if type(orderBy) in (types.TupleType, types.ListType):
          orderBy = [cls._sqlFields[x] for x in orderBy]
          orderBy = ',\n   '.join(orderBy)
        else:
          orderBy = cls._sqlFields[orderBy]
        sql += orderBy
      return (sql, fields)
        
    elif operation in ('INSERT', 'UPDATE'):
      if operation == 'UPDATE':
        sql = 'UPDATE %s SET\n  ' % cls._sqlTable
      else:
        sql = 'INSERT INTO %s (\n  ' % cls._sqlTable
        
      set = []
      fields = []
      sqlfields = []
      for (field, sqlfield) in cls._sqlFields.items():
        if operation == 'UPDATE' and field in cls._sqlPrimary:
          continue
        if sqlfield.find(cls._sqlTable + '.') == 0:
          # It's a local field, chop of the table part
          sqlfield = sqlfield[len(cls._sqlTable)+1:]
          fields.append(field)
          sqlfields.append(sqlfield)
          set.append(sqlfield + '=%s')
      if operation == 'UPDATE':
        sql += ',\n  '.join(set)    
        sql += '\nWHERE\n  '
        tempWhere = []
        for key in cls._sqlPrimary:
          tempWhere.append(cls._sqlFields[key] + "=%s")
          fields.append(key)
        sql += ' AND\n  '.join(tempWhere) 
      else:
        sql += ',\n  '.join(sqlfields)
        sql += ')\nVALUES (\n  '
        sql += ',\n  '.join(('%s',) * len(sqlfields))
        sql += ')'
        
      return (sql, fields)
      
    elif operation == 'DELETE':
      sql = 'DELETE FROM ' + cls._sqlTable + ' WHERE '
      if where:
        sql += " AND\n  ".join(where) 
      else:
        for key in cls._sqlPrimary:
          tempWhere = []
          for key in cls._sqlPrimary:
            tempWhere.append(cls._sqlFields[key] + "=%s")
        sql += ' AND\n  '.join(tempWhere) 
      return (sql, )      
    else:
      raise "Unknown operation", operation
      
  _prepareSQL = classmethod(_prepareSQL)
  
  def _nextSequence(cls, name=None):
    """Returns a new sequence number for insertion in self._sqlTable.
     Note that if your sequences are not named
     tablename_primarykey_seq  (ie. for table 'blapp' with primary key
     'john_id', sequence name blapp_john_id_seq) you must give the full 
     sequence name as an optional argument to _nextSequence)
    """
    if not name:
      name = cls._sqlSequence
    if not name:
      # Assume it's tablename_primarykey_seq
      if len(cls._sqlPrimary) <> 1:
        raise "Could not guess sequence name for multi-primary-key"
      primary = cls._sqlPrimary[0]
      name = '%s_%s_seq' % (cls._sqlTable, primary.replace('.','_'))
      # Don't have . as a tablename or column name! =)
    curs = cls.cursor()
    curs.execute("SELECT nextval('%s')" % name)
    value = curs.fetchone()[0]
    curs.close()
    return value

  _nextSequence = classmethod(_nextSequence)
 
  def _loadFromRow(self, result, fields, cursor):
    """Load from a database row, described by fields.
       fields should be the attribute names that 
       will be set. Note that userclasses will be
       created (but not loaded).  """
    position = 0
    for elem in fields:
      value = result[position]
      valueType = cursor.description[position][1]
      if valueType == self._dbModule.BOOLEAN and value not in (True, False):
        # convert to a python boolean
        value = value and True or False
      if value and self._userClasses.has_key(elem):
        userClass = self._userClasses[elem]
        # create an instance
        value = userClass(value)
        
      self._values[elem] = value
      position += 1

  def _loadDB(self):  
    """Connects to the database to load myself"""
    if not self._validID():
      raise NotFound, self._getID()
    (sql, fields) = self._prepareSQL("SELECT")
    curs = self.cursor()
    curs.execute(sql, self._getID()) 
    result = curs.fetchone()
    curs.close()
    if not result:
      raise NotFound, self._getID()
    self._loadFromRow(result, fields, curs)  
    self._updated = time.time()
  
  def _saveDB(self):
    """Inserts or updates into the database"""
    # We're a "fresh" copy now
    self._updated = time.time()
    if self._new:
      operation = 'INSERT'
      if not self._validID():
        self._setID(self._nextSequence())
      # Note that we assign this ID to our self
      # BEFORE possibly saving any of our attribute
      # objects that might be new as well. This means
      # that they might have references to us, as long
      # as the database does not require our existence
      # yet.
      #
      # Since mysql does not have Sequences, this will
      # not work as smoothly there. See class 
      # MysqlForgetter below.
    else:
      operation = 'UPDATE'
    (sql, fields) = self._prepareSQL(operation)  
    values = []
    for field in fields:
      value = getattr(self, field)
      if DateTime and type(value) in \
         (DateTime.DateTimeType, DateTime.DateTimeDeltaType):
        # stupid psycopg does not support it's own return type..
        # lovely..
        value = str(value)

      if value is True or value is False:
        # We must store booleans as 't' and 'f' ...  
        value = value and 't' or 'f'
      if isinstance(value, Forgetter):
        # It's another object, we store only the ID
        if value._new:
          # It's a new object too, it must be saved!
          value.save()
        try:  
          (value,) = value._getID()
        except:
          raise "Unsupported: Can't reference multiple-primary-key: %s" % value
      values.append(value)  
    cursor = self.cursor()
    cursor.execute(sql, values)
    # cursor.commit()
    cursor.close()
  
  def getAll(cls, where=None, orderBy=None):
    """Retrieves all the objects, possibly matching
       the where list of clauses, that will be AND-ed. 
       This will not load everything out
       from the database, but will create a large amount
       of objects with only the ID inserted. 
       The data will be loaded from the objects
       when needed by the regular load()-autocall."""
    ids = cls.getAllIDs(where, orderBy=orderBy)
    # Instansiate a lot of them
    return [cls(*id) for id in ids]
    
  getAll = classmethod(getAll)  
  
  def getAllIterator(cls, where=None, buffer=100, 
                     useObject=None, orderBy=None):
    """Retrieves every object, possibly limitted by the where
       list of clauses that will be AND-ed). Since this an
       iterator is returned, only buffer rows are loaded
       from the database at once. This is useful if you need
       to process all objects. If useObject is given, this object
       is returned each time, but with new data.
       """ 
    (sql, fields) = cls._prepareSQL("SELECTALL", where, orderBy=orderBy)
    curs = cls.cursor()
    fetchedAt = time.time()
    curs.execute(sql)

    # We might start eating memory at this point
    
    def getNext(rows=[]):
      forgetter = cls
      if not rows:
        rows += curs.fetchmany(buffer)
      if not rows:
        curs.close()
        return None
      row = rows[0]
      del rows[0]
      try:
        idPositions = [fields.index(key) for key in cls._sqlPrimary]
      except ValueError:
        raise "Bad sqlPrimary, should be a list or tupple: %s" % cls._sqlPrimary
      ids = [row[pos] for pos in idPositions]
      if useObject:
        result = useObject
        result.reset()
        result._setID(ids)
      else:  
        result = forgetter(ids)
      result._loadFromRow(row, fields, curs)
      result._updated = fetchedAt
      return result
    
    return iter(getNext, None)

  getAllIterator = classmethod(getAllIterator)

  def getAllIDs(cls, where=None, orderBy=None):
    """Retrives all the IDs, possibly matching the
       where clauses. Where should be some list of 
       where clauses that will be joined with AND). Note
       that the result might be tuples if this table
       has a multivalue _sqlPrimary."""
     
    (sql, fields) = cls._prepareSQL("SELECTALL", where, 
                                    cls._sqlPrimary, orderBy=orderBy)
    curs = cls.cursor()
    curs.execute(sql)
    # We might start eating memory at this point
    rows = curs.fetchall()
    curs.close()
    result = [] 
    idPositions = [fields.index(key) for key in cls._sqlPrimary]
    for row in rows: 
      ids = [row[pos] for pos in idPositions]
      if len(idPositions) > 1:
        ids = tuple(ids)
      else:
        ids = ids[0]
      result.append((ids))
    return result  
    
  getAllIDs = classmethod(getAllIDs)

  def getAllText(cls, where=None, SEPERATOR=' ', orderBy=None):
    """Retrieves a list of of all possible instances of this class. 
    The list is composed of tupples in the format (id, description) -
    where description is a string composed by the fields from
    cls._shortView, joint with SEPERATOR.

    """
    (sql, fields) = cls._prepareSQL("SELECTALL", where, orderBy=orderBy)
    curs = cls.cursor()
    curs.execute(sql)
    # We might start eating memory at this point
    rows = curs.fetchall()
    curs.close()
    result = []  
    idPositions = [fields.index(key) for key in cls._sqlPrimary]
    shortPos = [fields.index(short) for short in cls._shortView]
    for row in rows: 
      ids = [row[pos] for pos in idPositions]
      if len(idPositions) > 1:
        ids = tuple(ids)
      else:
        ids = ids[0]
      text = SEPERATOR.join([str(row[pos]) for pos in shortPos])
      result.append((ids, text))
    return result  

  getAllText = classmethod(getAllText)  
  
  def getChildren(self, forgetter, field=None, where=None, orderBy=None):
    """Returns the children that links to me. That means that I have
       to be listed in their _userClasses somehow. If field is
       specified, that field in my children is used as the pointer
       to me. Use this if you have multiple fields referring to
       my class."""
    if type(where) in (types.StringType, types.UnicodeType):
      where = (where,)
      
    if not field:
      for (i_field, i_class) in forgetter._userClasses.items():
        if isinstance(self, i_class):
          field = i_field
          break # first one found is ok :=)
    if not field:
      raise "No field found, check forgetter's _userClasses"
    sqlname = forgetter._sqlFields[field]  
    myID = self._getID()[0] # assuming single-primary !
    
    whereList = ["%s='%s'" % (sqlname, myID)]
    if where:
      whereList.extend(where)
    
    return forgetter.getAll(whereList, orderBy=orderBy)
    
  def __repr__(self):
    return self.__class__.__name__ + ' %s' % self._getID()
  
  def __str__(self):
    short = [str(getattr(self, short)) for short in self._shortView]
    text = ', '.join(short)
    return repr(self) + ': ' + text

class MysqlForgetter(Forgetter):
  """MYSQL-compatible Forgetter"""
  def _saveDB(self):
    """Overloaded - we dont have nextval() in mysql"""
    # We're a "fresh" copy now
    self._updated = time.time()
    if not self._validID():
      operation = 'INSERT'
      self._resetID() # Ie. get a new one
    else:
      operation = 'UPDATE'
    (sql, fields) = self._prepareSQL(operation)  
    values = []
    for field in fields:
      value = getattr(self, field)
      if isinstance(value, Forgetter):
        # It's another object, we store only the ID
        if value._new:
          # It's a new object too, it must be saved!
          value.save()
        try:  
          (value,) = value._getID()
        except:
          raise "Can't reference multiple-primary-key: %s" % value
      values.append(value)  
    cursor = self.cursor()
    cursor.execute(sql, values)
    # cursor.commit()

    # Here's the mysql magic to get the new ID
    self._setID(cursor.insert_id())
    cursor.close()

def prepareClasses(locals):
  """Fix _userClasses and some stuff in classes.
    Traverses locals, which is a locals() dictionary from
    the namespace where Forgetter subclasses have been 
    defined, and resolves names in _userClasses to real
    class-references.

    Normally you would call forgettSQL.prepareClasses(locals())
    after defining all classes in your local module.
    prepareClasses will only touch objects in the name space
    that is a subclassed of Forgetter."""
  for (name, forgetter) in locals.items():
    if not (type(forgetter) is  types.ClassType  and
            issubclass(forgetter, Forgetter)):
      # Only care about Forgetter objects
      continue
      
    # Resolve classes  
    for (key, userclass) in forgetter._userClasses.items():
      if type(userclass) is types.StringType:
        # resolve from locals
        resolved = locals[userclass]
        forgetter._userClasses[key] = resolved
        
    forgetter._tables = {}  
    # Update all fields with proper names
    for (field, sqlfield) in forgetter._sqlFields.items():
      forgetter._sqlFields[field] = forgetter._checkTable(sqlfield)
    
    newLinks = []
    for linkpair in forgetter._sqlLinks:
      (link1, link2) = linkpair
      link1=forgetter._checkTable(link1)
      link2=forgetter._checkTable(link2)
      newLinks.append((link1, link2))

    forgetter._sqlLinks = newLinks  
    forgetter._prepared = 1

