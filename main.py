import os
import json
import requests
from dotenv import load_dotenv
from persistence import PersistenceConfiguration, Persistence

load_dotenv('.env')

METADATA_BROKER_URLS = os.getenv("METADATA_BROKER_URLS").split(',')
METADATA_BROKER_DOCKER_URL = os.getenv("METADATA_BROKER_DOCKER_URL")
CONNECTOR_URL = os.getenv("CONNECTOR_URL")
CONNECTOR_USER = os.getenv('CONNECTOR_USER')
CONNECTOR_PW = os.getenv('CONNECTOR_PW')

DB_URI = os.getenv('DB_URI')
DB_NAME = os.getenv('DB_NAME')
BROKER_COLLECTION = os.getenv('BROKER_COLLECTION')
PROVIDER_COLLECTION = os.getenv('PROVIDER_COLLECTION')
RESOURCE_COLLECTION = os.getenv('RESOURCE_COLLECTION')
CATALOG_COLLECTION = os.getenv('CATALOG_COLLECTION')


# Get broker description
def get_broker_description(metadata_broker_url: str) -> dict:
    response = requests.get(metadata_broker_url, verify=False)
    print(" \t * Request GET {0} \t => {1}".format(metadata_broker_url, response.status_code))
    content = response.content
    description = json.loads(content)

    catalog_lists = []
    for resourceCatalog in description.get("ids:resourceCatalog", []):
        for offeredResource in resourceCatalog.get("ids:offeredResource", []):
            for representation in offeredResource.get("ids:representation", []):
                for instance in representation.get("ids:instance", []):
                    catalog_list = instance.get("@id")
                    if catalog_list:
                        catalog_lists += [catalog_list]
    description["_catalog_lists"] = list(set(catalog_lists))
    return description


def get_broker_catalogs(metadata_broker_url: str,broker_catalog_lists: list,  connector_url: str, auth: tuple) -> list:
    catalogs = {}

    for catalog in broker_catalog_lists:
        request_url = "{0}/api/ids/description?recipient={1}&elementId={2}"\
                      .format(connector_url, metadata_broker_url, catalog)
        response = requests.post(request_url, data={}, auth=auth, verify=False)
        print(" \t * Request POST {0} \t => {1}".format(request_url, response.status_code))
        content = response.content
        broker_graph = json.loads(content).get('@graph', [])
        for element in broker_graph:
            if element.get("@type") == "ids:BaseConnector" and element.get("@id"):
                if catalog not in catalogs.keys():
                    catalogs[catalog] = []
                catalogs[catalog] += [{"@id": element.get("@id")}]
    broker_catalogs = [{'@id': c, '@type': "ids:BaseConnector", 'connectors': l} for c, l in catalogs.items()]
    return broker_catalogs


def get_broker_connectors(metadata_broker_url: str, broker_catalogs: list, connector_url: str, auth: tuple) -> list:
    catalogs_wit_urls = []

    for catalog in broker_catalogs:
        connectors_with_urls = []
        for connector in catalog['connectors']:
            connector_id = connector['@id']
            request_url = "{0}/api/ids/description?recipient={1}&elementId={2}"\
                          .format(connector_url, metadata_broker_url, connector_id)
            response = requests.post(request_url, data={}, auth=auth, verify=False)
            print(" \t * Request POST {0} \t => {1}".format(request_url, response.status_code))
            content = response.content
            broker_graph = json.loads(content).get('@graph', [])
            for element in broker_graph:
                if element.get("@type") and element.get("@type") == "ids:ConnectorEndpoint" \
                        and element.get("accessURL"):
                    connector["accessURL"] = str(element.get("accessURL"))
                    connectors_with_urls += [connector]
        catalog['connectors'] = connectors_with_urls
        catalogs_wit_urls += [catalog]

    return catalogs_wit_urls


def get_provider_description(broker_doc: dict, connector_url: str, auth: tuple) -> list:
    providers = []

    for broker_catalog in broker_doc['_broker_catalogs']:
        for broker_connector in broker_catalog['connectors']:
            provider_url = broker_connector['accessURL']
            request_url = "{0}/api/ids/description?recipient={1}".format(connector_url, provider_url)
            response = requests.post(request_url, data={}, auth=auth, verify=False)
            print(" \t * Request POST {0} \t => {1}".format(request_url, response.status_code))
            provider = json.loads(response.content)
            provider["_broker_id"] = broker_doc['@id']
            provider["_broker_catalog_id"] = broker_catalog['@id']
            provider["_broker_connector_id"] = broker_connector['@id']
            provider["_provider_url"] = provider_url
            resource_catalogs = provider.get('ids:resourceCatalog', [])
            provider["_catalogs"] = []
            for element in resource_catalogs:
                if element.get("@type") and element.get("@type") == "ids:ResourceCatalog" and element.get("@id"):
                    provider["_catalogs"] += [{"@id": str(element.get("@id")), "@type": "ids:ResourceCatalog"}]
            providers += [provider]

    return providers


def get_sample_data(provider_url, sample_resource, connector_url, auth) -> dict:
    artifact_id = sample_resource['ids:representation'][0]['ids:instance'][0]['@id']
    resource_id = sample_resource['@id']
    rule_id = sample_resource['ids:contractOffer'][0]["ids:permission"][0]["@id"]

    body = [{
        "@type": "ids:Permission",
        "@id": rule_id,
        "ids:description": [{
            "@value": "Usage policy provide access applied",
            "@type": "http://www.w3.org/2001/XMLSchema#string"
        }],
        "ids:title": [{
            "@value": "Example Usage Policy",
            "@type": "http://www.w3.org/2001/XMLSchema#string"
        }],
        "ids:action": [{
            "@id": "https://w3id.org/idsa/code/USE"
        }],
        "ids:target": artifact_id
    }]

    request_url = "{0}/api/ids/contract".format(connector_url)
    params = {"recipient": provider_url, "resourceIds": resource_id, "artifactIds": artifact_id, "download": "false"}
    response = requests.post(request_url, json=body, params=params, auth=auth, verify=False)
    print(" \t\t\t\t - Request POST negotiation SAMPLE {0} {1} \t => {2}".format(sample_resource["resource_name"],
                                                                                 request_url, response.status_code))
    response.raise_for_status()
    agreement = json.loads(response.content)

    # request artifact data link from agreement id
    request_url = agreement["_links"]["artifacts"]["href"].split('{')[0]
    response = requests.get(request_url, auth=auth, verify=False)
    print(" \t\t\t\t - Request GET data link SAMPLE {0} {1} \t => {2}".format(sample_resource["resource_name"],
                                                                              request_url, response.status_code))
    response.raise_for_status()
    content = json.loads(response.content)

    # get the data
    request_url = content["_embedded"]["artifacts"][0]["_links"]["data"]["href"]
    response = requests.get(request_url, auth=auth, verify=False)
    print(" \t\t\t\t - Request GET data for SAMPLE {0} {1} \t => {2}".format(sample_resource["resource_name"],
                                                                             request_url, response.status_code))
    response.raise_for_status()
    data_content = json.loads(response.content)

    return data_content


def get_provider_catalog_description(provider_docs: list, connector_url: str, auth: tuple) -> (list, list):
    catalogs = []
    resources = []

    for provider in provider_docs:
        provider_url = provider["_provider_url"]
        for provider_catalog in provider["_catalogs"]:
            provider_catalog_id = provider_catalog['@id']
            request_url = "{0}/api/ids/description?recipient={1}&elementId={2}".format(connector_url, provider_url,
                                                                                       provider_catalog_id)
            response = requests.post(request_url, data={}, auth=auth, verify=False)
            print(" \t * Request POST {0} \t => {1}".format(request_url, response.status_code))
            content = response.content
            catalog = json.loads(content)

            catalog["_provider_id"] = provider['@id']
            for k in ["_broker_id", "_broker_catalog_id", "_broker_connector_id", "_provider_url"]:
                catalog[k] = provider[k]

            # this call does not return the samples attribute for the resources
            catalog_resources = catalog["ids:offeredResource"]
            catalog["ids:offeredResource"] = [str(r['@id']) for r in catalog_resources]
            catalogs += [catalog]

            samples = []
            for resource in catalog_resources:
                for k in ["_broker_id", "_broker_catalog_id", "_broker_connector_id", "_provider_url", "_provider_id"]:
                    resource[k] = catalog[k]
                resource["_catalog_id"] = str(catalog['@id'])
                sample = resource.get("ids:sample", {}).get('@id')
                if sample:
                    print("\t * SAMPLE found", sample)
                    # retrieve sample data and add to resource
                    sample_resources = [s for s in catalog_resources
                                        if s['@id'].split('/')[-1] == sample.split('/')[-1]]
                    if len(sample_resources) > 0:
                        sample_resource = sample_resources[0]
                        samples += [sample_resource['@id']]
                        resource['_sample_value'] = get_sample_data(provider_url, sample_resource, connector_url, auth)

                resources += [resource]

            # mark sample resource as sample
            for resource in catalog_resources:
                if resource['@id'] in samples:
                    resource['_is_sample'] = True

    # remove samples
    resources = [r for r in resources if not r.get('_is_sample', False)]
    return catalogs, resources


def init_persistence(db_uri: str = DB_URI, db_name: str = DB_NAME,
                     broker_collection_name: str = BROKER_COLLECTION,
                     provider_collection_name: str = PROVIDER_COLLECTION,
                     catalog_collection_name: str = CATALOG_COLLECTION,
                     resource_collection_name: str = RESOURCE_COLLECTION) -> Persistence:
    config = PersistenceConfiguration(db_uri, db_name, broker_collection_name, provider_collection_name,
                                      catalog_collection_name, resource_collection_name)

    persistence = Persistence(config)
    return persistence


def main(metadata_broker_urls: str = METADATA_BROKER_URLS, metadata_broker_docker_url: str = METADATA_BROKER_DOCKER_URL,
         connector_url: str = CONNECTOR_URL, connector_user: str = CONNECTOR_USER, connector_pw: str = CONNECTOR_PW,
         db_uri: str = DB_URI, db_name: str = DB_NAME):

    persistence = init_persistence()

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    for metadata_broker_url in metadata_broker_urls:
        # Use a breakpoint in the code line below to debug your script.
        print('Metadata Browser started... \n Setup:')  # Press ⌘F8 to toggle the breakpoint.
        print('\t - METADATA_BROKER_URL: {0}'.format(metadata_broker_url))  # Press ⌘F8 to toggle the breakpoint.
        print('\t - DB_URI: {0}, DB_NAME: {1}'.format(db_uri, db_name))  # Press ⌘F8 to toggle the breakpoint.

        print("\n 0. Requesting broker self-description...")
        broker_description = get_broker_description(metadata_broker_url)
        broker_doc = persistence.save_broker(broker_description)
        print("\t - Saved broker '{}' ({}, {})".format(broker_doc["_name"], broker_doc["@id"], broker_doc["_id"]))
        print("\t - Got {} catalog list(s) ({}...)".format(len(broker_doc["_catalog_lists"]),
                                                           ', '.join(broker_doc["_catalog_lists"])[:50]))
        print("\n 1. Query broker list of catalog(s)...")
        broker_catalog_lists = broker_doc["_catalog_lists"]
        connector_auth = (connector_user, connector_pw)
        broker_doc["_broker_catalogs"] = get_broker_catalogs(metadata_broker_docker_url, broker_catalog_lists,
                                                             connector_url, connector_auth)
        print("\t - Got {} catalog(s) ({}...)".format(len(broker_doc["_broker_catalogs"]),
                                                      str(broker_doc["_broker_catalogs"])[:200]))
        broker_doc = persistence.save_broker(broker_doc)

        print("\n 2. Request broker connectors info...")
        broker_catalogs = broker_doc["_broker_catalogs"]
        broker_doc["_broker_catalogs"] = get_broker_connectors(metadata_broker_docker_url, broker_catalogs,
                                                               connector_url, connector_auth)

        print("\t - Got {} catalog(s) with connector(s) ({}...)".format(len(broker_doc["_broker_catalogs"]),
                                                                        str(broker_doc["_broker_catalogs"])[:200]))
        broker_doc = persistence.save_broker(broker_doc)

        print("\n 3. Request each provider self-description...")
        provider_docs = get_provider_description(broker_doc, connector_url, connector_auth)
        print("\t - Got {} provider(s) description(s) ({}...)".format(len(provider_docs),
                                                                      str(provider_docs)[:200]))
        provider_docs = persistence.save_providers(provider_docs)

        print("\n 4. Request each provider catalog description...")
        catalog_docs, resource_docs = get_provider_catalog_description(provider_docs, connector_url, connector_auth)
        catalog_docs = persistence.save_catalogs(catalog_docs)
        resource_docs = persistence.save_resources(resource_docs)
        print("\t - Got {} provider catalog(s) description(s) ({}...)".format(len(catalog_docs),
                                                                              str(catalog_docs)[:500]))
        print("\t - Got {} provider resource(s) ({}...)".format(len(resource_docs), str(resource_docs)[:500]))

        print("\t... DONE.")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
