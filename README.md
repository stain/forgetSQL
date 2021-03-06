# forgetSQL

* Author: Stian Soiland-Reyes <stian@soiland-reyes.com>
* Homepage: https://github.com/stain/forgetSQL
* License: [GNU Lesser General Public License (LGPL) 2.1](http://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html)
   or later. See the file [COPYING](COPYING) for details.
* Status: **not maintained** _This repository is provided for archival purposes_

forgetSQL is a Python module for accessing SQL databases by creating
classes that maps SQL tables to objects, normally one class pr. SQL
table. The idea is to forget everything about SQL and just worrying
about normal classes and objects.

# Download

See the [GitHub releases](https://github.com/stain/forgetSQL/releases)
for the latest downloads, or check out from the
GitHub project [stain/forgetSQL](https://github.com/stain/forgetSQL).

# Installation

Installation of the forgetSQL module is pretty straight
forward:

    python setup.py install

This will install `forgetSQL.py` into `site-packages/` of your
Python distribution.


## Dependencies


* Python 2.2.1 or newer
* Some database module (tested: `MySQLdb`, `psycopg`)

If using `psycopg`, then `mx.DateTime` is needed to avoid a psycopg
bug related to re-inserting dates. `psycopg` depends on `mx.DateTime`, so
that shouldn't normally be a problem.


# What is forgetSQL?

## Why forgetSQL?

Let's start by showing an example using an imaginary database
`mydatabase`:

This example is based on these SQL tables:

**account**

accountid   | fullname          | groupid
----------- | ----------------- | --------
stain       | Stian Soiland     | 15
magnun      | Magnus Nordseth   | 15
stornes     | Sverre Stornes    | 17
mjaavatt    | Erlend Mjaavatten | 15


**group**

groupid | name
------- | -----
15      | unix
17      | tie


And your Python script should output something like:

    Account details for Stian Soiland
    Group unix (15)
    Other members:
    Magnus Nordseth
    Erlend Mjaavatten


In regular SQL programming, this could be done something like this:

```python
cursor = dbconn.cursor()
cursor.execute("SELECT fullname,groupid FROM account WHERE accountid=%s",
               ('stain',))
fullname,groupid = cursor.fetchone()
print "Account details for", fullname

cursor.execute("SELECT name FROM group WHERE groupid=%s" % groupid)
(groupname,) = cursor.fetchone()
print "Group %s (%s)" % (groupid, name)

cursor.execute("""SELECT fullname
                  FROM account JOIN group USING (groupid)
                  WHERE group.groupid=%s AND
                        NOT account.accountid=%s""",
               (groupid, accountid))
print "Other members:"
for (membername,) in cursor.fetchall():
    print membername
```

Now, using forgetSQL:

```python
    from mydatabase import *
    account = Account("stain") # primary key
    print "Account details for", account.fullname
    group = account.group
    print "Group %s (%s)" % (group.name, group.groupid)
    print "Other members: "

    for member in group.getChildren(Account):
        # find Account with group as foreign key
        if member <> account:
            print member.fullname
```

Notice the difference in size and complexity of these two examples.

The first example is tightly bound against SQL. The programmer is forced
to think about SQL instead of the real code. This programming style
tends to move high-level details to SQL, even if it is not neccessary.
In this example, when getting "other members", the detail of skipping
the active user is done in SQL.

This would hardly save any CPU time on modern computers, but has made
the code more complex.  Thinking in SQL makes your program very large,
as everything can be solved by some specialized SQL. Trying to change
your program or database structure at a later time would be a nightmare.

Now, forgetSQL removes all those details for the every-day-SQL tasks. It
will not be hyper-effective or give you points in the
largest-join-ever-possible-contest, but it will help you focus on what
you should be thinking of, making your program work.

If you at a later point (when everything runs without failures)
discovers that you need to optimize something with a mega-query in SQL,
you could just replace that code with regular SQL operations.
Of course, if you've been using test-driven development
your tests will show if the replaced code works.

Another alternative could be to use _views_ and _stored procedures_, and
layer forgetSQL on top of those views and procedures. This has never
been tested, though. =)

## What does forgetSQL do?

For each table in your database, a class is created. Each instance
created of these classes refer to a row in the given table. Each
instance have attributes that refer to the fields in the database.
Note that the instance is not created until you access that particular
row.

So accessing a column of a row is simply accessing the attribute
`row.column`.  Now, if this column is a reference to another table, a
foreign key, instead of an identifier you will in `row.column` find an
instance from the other table, ie. from the other class.

This is what happens in the example above, `group = account.group`
retrieves this instance. Further attribute access within this instance
is resolved from the matching row in the group table.

If you want to change some value, you could just change the attribute
value. In the example, if you want to change my name, simply run
`account.fullname = "Knut Carlsen"`

You can retrieve every row in some table that refers to the current
object. This is what happens in `group.getChildren(Account)`, which will
return a list of those Accounts that have a foreign key refering to
`group`.

If you retrieve the objects several times, the constructor will return
the same object the second time (unless some timeout has expired). This
means that changes done to the object is immediately visible to all
instances. This is to reflect normal behaviour in object oriented
programming. Example:

    >>> stain = Account("stain")
    >>> stain2 = Account("stain")
    >>> stain.fullname = "Stian Soiland-Reyes"
    >>> print stain2.fullname
    Stian Soiland-Reyes


## What does forgetSQL not do?

forgetSQL is not a way to store objects in a database. It is a way to
use databases as objects. You cannot store arbitrary objects in the
database unless you use pickling.

forgetSQL does not help you with database design, although you might
choose a development style that uses regular classes and objects at
first, and then design the database afterwards. You could then change
your classes to use forgetSQL for data retrieval and storage, and later
possibly replace forgetSQL classes with even more advanced objects.

forgetSQL does not remove the need of heavy duty SQL. In some
situations, SQL is simply the best solution. forgetSQL might involve
many SQL operations for something that could be done in a single
operations with a large magic query. If something does not scale up
with forgetSQL, even if you refactored your code, you might try using
SQL instead.  This example would use excessive time in a table with a
million rows:


```python
for row in table.getAll():
    row.backedUp = True
    row.save()
```

This would involve creating one million object instances (each row), one
million SELECTs (to get the other values that needs to be saved), and
one million UPDATEs.  By using `getAllIterator` you could reduce this to
just one million UPDATEs (one SELECT, reusing the same object), but
still it would be far much slower than `UPDATE table SET
backedUp=true`.

forgetSQL does not support commits/rollback. This might be implemented
later, but I'm still unsure of how to actually use this in programming.
Any suggestions are welcome.

### Keeping in sync

forgetSQL does not ensure that objects in memory are in sync with what
is stored in the database. The values in the object will be a snapshot
of how the row were at the time you first tried to retrieve an
attribute. If you change some value, and then save the object, the row
is updated to your version, no matter what has happened in the database
meanwhile. An object does not timeout while in memory, it does not
refresh it's values unless you call `_loadDB()` manually, as
automatically updating could confuse programmers. However, a timeout
value is set, and if exceeded, *new* objects retrieved from database
(ie. `Account("stain")` will be fresh.

It is not easy to make a general way to ensure objects are updated. For
instance, always checking it could be heavy. It could also confuse some
programs if an object suddenly changes some of it's attributes without
telling, this could fuck up any updates the program is attempting to do.
On the other hand, saving a changed object as forgetSQL is now, will
overwrite *all* attributes, not just the changed ones.


# Usage

## forgetsql-generate

Before you can use forgetSQL, you will need to generate a module
containg the classes representing database tables. Luckily, forgetSQL
ships with a program that can do this for you by guessing.

The program is called `forgetsql-generate` and should be installed by
`setup.py` or the packaging system. You might need the devel-version
of the forgetSQL package.

Create a file `tables.txt`, with a list of database tables, one per
line. (This is needed since there is no consistent way to query a
database about it's tables)

Then generate the module representing your tables:

    forgetsql-generate --dbmodule psycopg --username=johndoe
                         --password=Jens1PuLe --database=genious
                         --tables tables.txt --output Genious.py

Alternative, you could pipe the table list to `forgetsql-generate`
and avoid `--tables` -- and likewise drop `--output` and capture stdout
from forgetsql-generate.

The generated module is ready for use, except that you need to
set database connecting details. One possible way is included in the
generated code, commented out and without a password.

It is recommended to set connection details from the outside instead,
since the tables might be used by different parts of a system using
different database passwords, connection details could be in a
configuration file, you need persistent database connections, etc.

The way to do this is to set `Genious._Wrapper.cursor` to a cursor
method, and `Genious._Wrapper._dbModule` to the database module used:

```Python
import Genious
import psycopg
conn = psycopg.connect(user="blal", pass="sdlksdlk", database="blabla")
Genious._Wrapper.cursor = conn.cursor()
Genious._Wrapper._dbModule = psycopg
```


## Normal use

We'll call a class that is a representation of a database table a
forgetter, because it inherits `forgetSQL.Forgetter`.
This chapter will present normal usage of such forgetters by examples.

### Getting a row by giving primary key

Example:

```python
account = Account("stain")
print account.fullname
```

If the primary key is wrong (ie. the row does not exist) accessing
`account.fullname` will raise `forgetSQL.NotFound`. The object is
actually not loaded from the database until a attribute is read.
(delayed loading) One problem with that is that `forgetSQL.NotFound`
will not be raised until the attribute is read.

To test if the primary key is valid, force a load:

```python
account = Account("stain")
try:
    account.load()
except forgetSQL.NotFound():
    print "Cannot find stain"
    return
```

### Getting all rows in a table

Example:

```python
allAccounts = Account.getAll()
for account in allAccounts:
    print account.accountid, account.fullname
```

Note that `getAll` is a class method, so it is available even before
creating some `Account`. The returned list will be empty if nothing is
found.

Also note that if what you want to do is to iterate, using
`getAllIterator()` would work well. This avoids creating all objects
at once.

### To create a new row in a table

Example:

```python
account = Account()
account.accountid = "jennyme" # primary key
account.fullname = "Jenny Marie Ellingsaeter"
account.save()
```

If you have forgotten to set some required fields, save() will fail. If
you don't set the primary key, forgetSQL will try to guess the sequence
name (`tablename_primarykey_seq`) to retrieve a new one. This might or
might not work. For MySQL some other magic is involved, but it should
work.


### Change some attribute

Example:

```python
account = Account("stain")
account.fullname = "Stian Stornes" # got married to a beautiful man
```

You can choose wether you want to call `save()` or not. If you don't call
`save()`, the object will be saved when the object reference disappaers
(ie. del account, end of function, etc.) and collected by the garbage
collector. Note that this might be delayed, and that any errors
will be disgarded.

If you are unsure if you have used the correct data type or want to
catch save-errors, use `save()`:

```python
group = Group(1)
group.accountid = 'itil' # a string won't work in a integer field
try:
    group.save()
except Exception, e:
    print "Could not save group %s: %s" % (group, e)
```

The exception raised will be database module specific, like
`psycopg.ProgrammingError`, possible containing some useful information.

`save()` will return `True` if successful.

### Undoing an attribute change

If you changed an attribute, and you don't want to save the change to
the database (as this will happen when the garbage collector kicks in),
you have two choices:

Reset the instance to a blank state:

  ```python
       group.reset()
  ```

This sets everything to `None`, including the primary key.
If you have referenced the instance anywhere else, they
will now experience a blank instance.

Or reload from database:

```python
group.load()
```
Note, `load()` will perform a new SELECT.  

Note that you don't have to `reset()` if you haven't changed any
attributes, the instance will only save if anything has changed.


### Accessing foreign keys

Example:

```python
account = Account("stain")
print account.group.accountid
print account.group.name
```

An attribute which is a foreign key to some other table will be
identified by forgetsql-generate if it's name is something like
`other_table_id`. If the generator could not identify foreign keys
correctly, modify `_userClasses` in the generated  Forgetter
definition. (See _Specializing the forgetters_).

To access the real primary key, use account.group.accountid or
`account.group._getID()`. Note that the latter will return a tupple
(in case the primary key contained several columns).o

You can set a foreign key attribute to a new object from the
foreign class:

```python
import random
allGroups = Group.getAll()
for account in Account.getAll():
    # Set the group to one of the Group instances
    # in allGroups
    account.group = random.choice(allGroups)
del account
# Note that by reusing the account variable all of these
# will be saved by the garbage collector
```

or to just the foreign primary key:

```python
account.group = 18
```

Note that this referencing magic makes JOIN unneccessary in many cases,
but be aware that due to lazy loading (attributes are not loaded from
database before they are accessed for the first time), in some cases
this might result in many SELECT-calls. There are ways to avoid this,
see _Wrapping SQL queries_.


### Finding foreign keys

You might want to walk in reverse, finding all accounts that have a
given group as a foreign key:

```python
group = Group(15)
members = group.getChildren(Account)
```

This is equivalent to SQL:

```sql
SELECT * FROM account WHERE groupid=15
```

### Deleting an instance

Note that although rows are represented as instances, they will not be
deleted from the database by dereferencing. Simply removing a name
binding only removes the representation. (and actually forces a
`save()` if anything has changed).

To remove a row from the database:

```python
account = Account("stornes")
account.delete()
```

`delete()` might fail if your database claims reference integrity but
does not cascade delete:

```python
group = Group(17)
group.delete()
```

## Advanced use

### WHERE-clasules

You may specify a where-sentence to be inserted into the SELECT-call of
`getAll`-methods:

```python
members = Account.getAll(where="groupid=17")
```

Note that you must take care of proper escaping on your own by using
this approach. Most database modules have some form of escape functions.

In many cases, what you want to do with WHERE is probably the
same as with `getChildren()`:

```python
group = Group(17)
members = group.getChildren(Account)
```

This will be as effective as generating a WHERE-clasule, since
`group.load()` won't be run (no attributes accessed, only the primary
key).

The sentence is directly inserted, so you need to use the actual SQL
column names, not the attribute names. You can use AND and OR as you
like.

If you have several clauses to be AND-ed together, forgetSQL can do this
for you, as the where-parameter can be a list:

```python
where = []
where.append("groupid=17")
if something:
    where.append("fullname like 'Stian%'")
Account.getAll(where=where)
```

### Sorting

If you have specified `_orderBy` (see _Specializing the forgetters_),
the results of `getAll*` and `getChildren` will be ordered by those
attributes.

If you want to specify ordering manually, you can supply a keyword
argument to `getAll``:

```python
all = Account.getAll(orderBy="fullname")
```

The value of `orderBy` could be either a string (representing the
object attribute to be sorted) or a tupple of strings (order by A, then
B, etc.). Note that you can only order by attributes defined in the
given table.

If you want some other fancy sorting, sort the list after retrieval
using regular `list.sort()`:

```python
all = Account.getAll()
all.sort(lambda a,b:
            cmp(a.split()[-1],
                b.split()[-1]))
# order by last name! :=)
```


### More getAll

There are specialized `getAll` methods for different situations.

If you just want the IDs in a table:

```python
>>> all = Account.getAllIDs()
['stornes', 'stain', 'magnun', 'mjaavatt']
```

The regular `getAll()` actually runs `getAllIDs()`, and returns a
list of instances based on those IDs. The real data is not loaded
until attribute access. In some cases, this might be OK, for instance if
you want to call getChildren and really don't care about the attribute
values.

If you are going to iterate through the list, a common case, use
instead:

```python
for account in Account.getAllIterator():
    print account.fullname
```

This will return an iterator, not a list, returning `Account` objects.
For each iteration, a new instance is returned, with all fields
loaded. Internally in the iterator, a buffer of results from SELECT * is
contained.

In Python, object creation is a bit expensive, so you might reuse the
same object for each iteration by creating it first and specifying it
as the keyword argument `useObject`:

```python
for account in Account.getAllIterator(useObject=Account()):
    print account.fullname
```

Note that changes made to account in this case will be flushed unless
you manually call `save()`. Do not pass this instance on, as it's content
will change for each iteration.

Finally, `getAllText()` will use `_shortView` (See _Specializing
the forgetters_) and return tuples of (id, text). This is useful for
a dropdown-list of selectors.


# Specializing the forgetters

By specifying the `Forgetter` subclasses manually, or correcting
the autogenerated ones from `forgetsql-generate`, you can fix any
mistakes in `_sqlFields`, etc.
