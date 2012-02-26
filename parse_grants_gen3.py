#!/usr/bin/python

from xml.sax import handler, make_parser, SAXException
import sys
import sqlite3

# handle arguments
if len(sys.argv) <= 1:
  print 'Usage: parse_grants_gen3.py filename store_db'
  sys.exit(0)

in_fname = sys.argv[1]
if sys.argv[2] == '1':
  store_db = True
else:
  store_db = False

if store_db:
  # database file
  db_fname = 'store/patents.db'
  conn = sqlite3.connect(db_fname)
  cur = conn.cursor()
  try:
    cur.execute("create table patent (patnum int, filedate text, grantdate text, owner text)")
  except sqlite3.OperationalError as e:
    print e

# store for batch commit
batch_size = 1000
patents = []

def commitBatch():
  if store_db:
    cur.executemany('insert into patent values (?,?,?,?)',patents)
  del patents[:]

# SAX hanlder for gen3 patent grants
class GrantHandler(handler.ContentHandler):
  def __init__(self):
    pass

  def startDocument(self):
    self.in_pubref = False
    self.in_appref = False
    self.in_patnum = False
    self.in_grantdate = False
    self.in_filedate = False
    self.in_assignee = False
    self.in_orgname = False

    self.completed = 0
    self.multi_assign = 0

  def endDocument(self):
    pass

  def startElement(self, name, attrs):
    if name == 'us-patent-grant':
      self.patnum = ''
      self.grant_date = ''
      self.file_date = ''
      self.orgname = ''
    elif name == 'publication-reference':
      self.in_pubref = True
    elif name == 'application-reference':
      self.in_appref = True
    elif name == 'doc-number':
      if self.in_pubref:
        self.in_patnum = True
    elif name == 'date':
      if self.in_pubref:
        self.in_grantdate = True
      elif self.in_appref:
        self.in_filedate = True
    elif name == 'assignee':
      self.in_assignee = True
      if len(self.orgname) > 0:
        self.multi_assign += 1
      self.orgname = ''
    elif name == 'orgname':
      if self.in_assignee:
        self.in_orgname = True

  def endElement(self, name):
    if name == 'us-patent-grant':
      if self.patnum[0] == '0':
        self.patint = int(self.patnum[1:])
        self.completed += 1
        self.addPatent()
    elif name == 'publication-reference':
      self.in_pubref = False
    elif name == 'application-reference':
      self.in_appref = False
    elif name == 'doc-number':
      self.in_patnum = False
    elif name == 'date':
      if self.in_grantdate:
        self.in_grantdate = False
      elif self.in_filedate:
        self.in_filedate = False
    elif name == 'assignee':
      self.in_assignee = False
    elif name == 'orgname':
      self.in_orgname = False

  def characters(self, content):
    if self.in_patnum:
      self.patnum += content
    if self.in_grantdate:
      self.grant_date += content
    if self.in_filedate:
      self.file_date += content
    if self.in_orgname:
      self.orgname += content

  def addPatent(self):
    #orgname_esc = self.orgname.encode('ascii','ignore')
    #print '{} {} {} {:.60}'.format(self.patint,self.file_date,self.grant_date,orgname_esc)

    patents.append((self.patint,self.file_date,self.grant_date,self.orgname))
    if len(patents) == batch_size:
      commitBatch()

# do parsing
parser = make_parser()
grant_handler = GrantHandler()
parser.setContentHandler(grant_handler)
parser.parse(in_fname)

# clear out the rest
if len(patents) > 0:
  commitBatch()

if store_db:
  # commit to db and close
  conn.commit()
  cur.close()
  conn.close()

print grant_handler.multi_assign
print grant_handler.completed


