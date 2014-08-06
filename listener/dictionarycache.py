"""SQLite DB with Word - ArpaBet correspondences"""
import sqlite3
import os
import logging
from .oneshot import one_shot
log = logging.getLogger( __name__ )

class DictionaryDB( object ):
    def __init__( self, context ):
        self.context = context 
    
    @one_shot
    def filename( self ):
        return self.context.dictionary_file + '.sqlite' 
    
    @one_shot
    def connection( self ):
        if not os.path.exists( self.filename ):
            return self.initialize(sqlite3.connect( self.filename ))
        return sqlite3.connect( self.filename )
    
    DATABASE_CREATION = [
    """CREATE TABLE IF NOT EXISTS dictionary( word text NOT NULL, arpa text, ipa text )""",
    """CREATE INDEX IF NOT EXISTS dictionary_words ON dictionary( word )""",
    """CREATE INDEX IF NOT EXISTS dictionary_arpa ON dictionary( arpa )""",
    """CREATE INDEX IF NOT EXISTS dictionary_ipa ON dictionary( ipa )""",
    ]
    
    def dictionary_iterator( self, dictionary_file, separator='\t' ):
        for i,line in enumerate(open(dictionary_file)):
            word,description = line.strip().split(separator,1)
            if word.endswith(')'):
                word = word.rsplit('(',1)[0]
            word = word.decode('utf-8')
            yield word.lower(),description.upper()

    def initialize( self, connection ):
        log.warn( 'Creating dictionary cache, may take a few seconds' )
        cursor = connection.cursor()
        for statement in self.DATABASE_CREATION:
            cursor.execute( statement )
        cursor.close()
        # TODO: add context.parent dictionaries recursively
        self.add_dictionary_file( self.context.dictionary_file )
        if os.path.exists( self.context.custom_dictionary_file ):
            self.add_dictionary_file( self.context.custom_dictionary_file )
        log.warn( 'Dictionary cache created' )
        return connection
    
    def add_dictionary_iterable( self, iterable ):
        """Add words from the given iterable"""
        connection = self.connection
        cursor = connection.cursor()
        cursor.executemany(
            "INSERT INTO dictionary( word, arpa ) VALUES (?,?)",
            iterable,
        )
        connection.commit()
    def add_dictionary_file( self, dictionary_file, separator='\t' ):
        return self.add_dictionary_iterable( self.dictionary_iterator( dictionary_file, separator ) )
    
    def have_words( self, *words ):
        """For each word in word, report all arpa values for them"""
        cursor = self.connection.cursor()
        results = {}
        for word in words:
            if isinstance( word, bytes ):
                word = word.decode('utf-8')
            if not word:
                continue
            word = word.lower()
            results[word] = []
            cursor.execute( 
                "SELECT arpa from dictionary where word = ?",
                [word],
            )
            for row in cursor.fetchall():
                results[word].append( row[0] )
        return results
    def __contains__( self, word ):
        return bool(self.have_words( word ).get(word))

usage = 'listener-dictionary-cache <words>\n'
def main():
    from . import context 
    import pprint, sys
    if not sys.argv[1:]:
        sys.stdout.write( usage )
        sys.exit(1)
    c = context.Context('default')
    db = DictionaryDB( c )
    pprint.pprint( db.have_words( *sys.argv[1:] ))
    db.connection.close()
