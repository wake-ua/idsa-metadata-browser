# idsa-metadata-browser
Collects the resources metadata from a IDSA broker

## Example execution:
 0. Requesting broker self-description...
 	 * Request GET https://localhost:444 	 => 200
	 - Saved broker 'IDS Metadata Broker' (https://localhost/, 668c5e7777eaa682d446dd23)
	 - Got 1 catalog list(s) (https://localhost/connectors/...)

 1. Query broker list of catalog(s)...
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://broker-reverseproxy/infrastructure&elementId=https://localhost/connectors/ 	 => 200
	 - Got 1 catalog(s) ([{'@id': 'https://localhost/connectors/', '@type': 'ids:BaseConnector', 'connectors': [{'@id': 'https://localhost/connectors/2129657530'}, {'@id': 'https://localhost/connectors/2129657531'}, {'@id': '...)

 2. Request broker connectors info...
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://broker-reverseproxy/infrastructure&elementId=https://localhost/connectors/2129657530 	 => 200
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://broker-reverseproxy/infrastructure&elementId=https://localhost/connectors/2129657531 	 => 200
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://broker-reverseproxy/infrastructure&elementId=https://localhost/connectors/2129657532 	 => 200
	 - Got 1 catalog(s) with connector(s) ([{'@id': 'https://localhost/connectors/', '@type': 'ids:BaseConnector', 'connectors': [{'@id': 'https://localhost/connectors/2129657530', 'accessURL': 'https://connectora:8080/api/ids/data'}, {'@id': ...)

 3. Request each provider self-description...
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://connectora:8080/api/ids/data 	 => 200
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://connectorb:8081/api/ids/data 	 => 200
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://connectorc:8082/api/ids/data 	 => 200
	 - Got 3 provider(s) description(s) ([{'@context': {'ids': 'https://w3id.org/idsa/core/', 'idsc': 'https://w3id.org/idsa/code/'}, '@type': 'ids:BaseConnector', '@id': 'https://connector_A', 'ids:description': [{'@value': 'IDS Connector A...)

 4. Request each provider catalog description...
 	 * Request POST https://localhost:8081/api/ids/description?recipient=https://connectora:8080/api/ids/data&elementId=https://connectora:8080/api/catalogs/dea6d917-3ebc-4acc-af91-d38cbaccb54e 	 => 200
	 - Got 1 provider catalog(s) description(s) ([{'_id': ObjectId('66995c1977eaa682d496deb3'), '@context': {'ids': 'https://w3id.org/idsa/core/', 'idsc': 'https://w3id.org/idsa/code/'}, '@type': 'ids:ResourceCatalog', '@id': 'https://connectora:8080/api/catalogs/dea6d917-3ebc-4acc-af91-d38cbaccb54e', 'ids:offeredResource': ['https://connectora:8080/api/offers/dc4cafaf-655c-4c2a-9ad4-ef13e8a3a3bf'], '_provider_id': 'https://connector_A', '_broker_id': 'https://localhost/', '_broker_catalog_id': 'https://localhost/connectors/', '_broker_connect...)
	 - Got 1 provider resource(s) ([{'_id': ObjectId('66a0c1aa77eaa682d49ab77f'), '@type': 'ids:Resource', '@id': 'https://connectora:8080/api/offers/dc4cafaf-655c-4c2a-9ad4-ef13e8a3a3bf', 'ids:language': [{'@id': 'https://w3id.org/idsa/code/DE'}], 'ids:description': [{'@value': 'DWD weather warnings for germany.', '@language': 'DE'}], 'ids:version': '1', 'ids:title': [{'@value': 'DWD Weather Warnings', '@language': 'DE'}], 'ids:representation': [{'@type': 'ids:Representation', '@id': 'https://connectora:8080/api/representations/...)
	... DONE.

Process finished with exit code 0
