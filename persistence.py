from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
import certifi


class PersistenceConfiguration:

    def __init__(self, db_uri: str, db_name: str,
                 broker_collection_name: str, provider_collection_name: str, catalog_collection_name: str,
                 resource_collection_name: str):
        self.db_uri = db_uri
        self.db_name = db_name
        self.broker_collection_name = broker_collection_name
        self.provider_collection_name = provider_collection_name
        self.catalog_collection_name = catalog_collection_name
        self.resource_collection_name = resource_collection_name


class Persistence:
    def __init__(self, config: PersistenceConfiguration):
        self.config = config
        if self.config.db_uri.find("localhost"):
            self.client = MongoClient(self.config.db_uri)
        else:
            self.client = MongoClient(self.config.db_uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())
        self.db = self.client[self.config.db_name]
        self.test_connection()

        self.broker_collection = self.db[self.config.broker_collection_name]
        self.provider_collection = self.db[self.config.provider_collection_name]
        self.catalog_collection = self.db[self.config.catalog_collection_name]
        self.resource_collection = self.db[self.config.resource_collection_name]

    def test_connection(self, test_collection: str = 'test') -> bool:
        try:
            # self.client.admin.command('ping')
            self.db[test_collection].replace_one({'success': True}, {'success': True}, upsert=True)
            doc = self.db[test_collection].find_one()
            print("* Connection to database '{}' => OK {}".format(self.db.name, doc))
            return True
        except Exception as e:
            raise Exception('ERROR: Cannot connect to db {}/{}, {}'.format(self.config.db_uri, self.config.db_name, e))

    @staticmethod
    def timestamp(doc: dict, collection: Collection, id_query: dict) -> dict:
        existing_doc = collection.find_one(id_query)
        if existing_doc:
            doc['_insert_timestamp'] = existing_doc["_insert_timestamp"]
        else:
            doc['_insert_timestamp'] = datetime.now()
        doc['_update_timestamp'] = datetime.now()
        return doc

    def save_broker(self, doc: dict) -> dict:
        id_query = {"@id": doc["@id"]}
        doc['_name'] = ([d.get('@value') for d in doc.get('ids:title', [])
                        if d.get('@language') == 'en'] + ['Unnamed Broker'])[0]
        return self.save_doc(doc, self.broker_collection, id_query)

    def save_providers(self, docs: list) -> list:
        inserted_docs = [self.save_provider(doc) for doc in docs]
        return inserted_docs

    def save_provider(self, doc: dict) -> dict:
        doc['_name'] = ([d.get('@value') for d in doc.get('ids:title', [])] + ['Unnamed Provider'])[0]
        id_query = {"@id": doc["@id"]}
        return self.save_doc(doc, self.provider_collection, id_query)

    def save_catalogs(self, docs: list) -> list:
        inserted_docs = [self.save_catalog(doc) for doc in docs]
        return inserted_docs

    def save_catalog(self, doc: dict) -> dict:
        id_query = {"@id": doc["@id"]}
        return self.save_doc(doc, self.catalog_collection, id_query)

    def save_resources(self, docs: list) -> list:
        inserted_docs = [self.save_resource(doc) for doc in docs]
        return inserted_docs

    def save_resource(self, doc: dict) -> dict:
        id_query = {"@id": doc["@id"]}
        return self.save_doc(doc, self.resource_collection, id_query)

    def save_doc(self, doc: dict, collection: Collection, id_query: dict):
        doc = self.timestamp(doc, collection, id_query)
        collection.replace_one(id_query, doc, upsert=True)
        inserted_doc = collection.find_one(id_query)
        return inserted_doc
