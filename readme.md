# NEO4j Uploader
This is a little script that uses a graph description as
json and uploads this to neo4j.

## JSON Graph Format

```JS
{
    "nodes": {
        // n1 - is the identifier of the node only used
        //      to create the edges of the graph and wont
        //      appear in neo4j
        // label - is the label of the node
        //         (a node can only have one label as of now)
        "n1": {"label": "<your label>"}

        // properties - are the properties that the node will
        //              receive (this is optional).
        //              Here the same rules as in neo4j
        //              apply. Meaning keys must be strings and
        //              values valid neo4j CORE types...
        //                  - strings
        //                  - integers
        //                  - floating point numbers
        //                  - booleans
        //                  - lists
        //                  - maps
        //
        //              see: https://neo4j.com/docs/python-manual/current/data-types/
        "n2": {"label": "<your label>", "properties": {"name": "Sojamann", "height": 183}}
    }

    "edges:" {
        // n1->n2 means create a directed relationship from
        //          n1 to n2 with the label and if set the
        //          properties
        //
        // n1<-n2 means create a directed releationship from
        //          n2 to n1 ....
        "n1->n2": {"label": "<your label", "properties: {...}}
    }
}
```

## Usage
### CLI Reference
```SH
usage: upload.py [-h] --host HOST [-p PORT] -u USER -pw PASSWORD [-d DATABASE] -f FILE [--no-prior-clear]

options:
  -h, --help            show this help message and exit
  --host HOST
  -p PORT, --port PORT                  The port of neo4j to connect to ... defaults to '7687'
  -u USER, --user USER                  The username for authentication
  -pw PASSWORD, --password PASSWORD     The password for authentication
  -d DATABASE, --database DATABASE      The database to connect to ... defaults to 'neo4j'
  -f FILE, --file FILE                  The json file with the graph description
  --no-prior-clear                      Do not clear the neo4j database prior to creating the graph
  --non-encrypted                       Tell the neo4j driver to not encrypt the data

```

### Starting Neo4j (Minimal container setup)
```SH
docker run -d \
    --name neo4j \
    --rm \
    -p 7474:7474 -p7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:latest

```

### Executig The Script
```SH
./upload.py --host localhost -p 7687 -u neo4j -pw password -f ./graph.json
```

