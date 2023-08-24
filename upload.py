#!/usr/bin/env python3
import re
import enum
import sys

from dataclasses import dataclass, field
from typing import Iterable, Dict

from neo4j import GraphDatabase, Transaction

NODE_ID_PATTERN = "[a-zA-Z0-9.,\-_ ]+"
EDGE_REGEX = re.compile(f"({NODE_ID_PATTERN})(<-|->)({NODE_ID_PATTERN})")

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable: Iterable, desc: str):
        for i, item in enumerate(iterable):
            print(
                f"{desc} - {round((i+1)/len(iterable)*100)}% ({i+1}/{len(iterable)})",
                file=sys.stderr
            )
            yield item

@dataclass
class Neo4jItem:
    label: str
    properties: Dict = field(default_factory=dict)

    OPENING = None
    CLOSING = None

    def query_str(self, identifier: str = "n") -> tuple[str, Dict]:
        """creates a string to be used in a neo4j query

        Args:
            identifier (str): how the node should be called in the query

        Returns:
            tuple[str, Dict]: the query string with its query parameters
        """
        
        # when creating a node with an empty property value e.g. 
        # 'CREATE (n: LABEL { prop: null })' neo4j wont store
        # the property of the node since it has no value.
        # When trying to later find the node, we therefore have to exclude
        # the key, value pair from the properties, otherwise we cannot
        # find the node again using e.g.
        # MATCH (n: {prop: null}) since this key value pair is not present
        # on any node/edge.
        properties = {k: v for k, v in self.properties.items() if v is not None}

        start = f"{identifier}: {self.label} "
        mid = "{" + ", ".join(f"{k}: ${identifier}_{k}" for k in properties) + "}"
        query_str = self.OPENING + start + mid + self.CLOSING

        return query_str, {f"{identifier}_{k}": v for k, v in properties.items()}

@dataclass
class Node(Neo4jItem):
    OPENING = "("
    CLOSING = ")"


@dataclass
class Edge(Neo4jItem):
    OPENING = "["
    CLOSING = "]"

    class Direction(enum.Enum):
        LEFT = enum.auto()
        RIGHT = enum.auto()


DIRECTION_NAME_TABLE = {
    "->": Edge.Direction.RIGHT,
    "<-": Edge.Direction.LEFT,
}


def create_node(
    tx: Transaction,
    node: Node,
) -> None:
    node_query_str, params = node.query_str()
    query = f"CREATE {node_query_str}"

    print(query, params)
    tx.run(query, params)

def create_edge(
    tx: Transaction,
    node1: Node,
    node2: Node,
    edge: Edge,
    direction: Edge.Direction,
) -> None:
    node1_query_str, node1_params = node1.query_str("n1")
    node2_query_str, node2_params = node2.query_str("n2")
    edge_query_str, edge_query_params = edge.query_str()

    left_symbol = "<-" if direction == Edge.Direction.LEFT else "-"
    right_symbol = "->" if direction == Edge.Direction.RIGHT else "-"

    query = f"""
        MATCH {node1_query_str}
        MATCH {node2_query_str}
        CREATE (n1){left_symbol}{edge_query_str}{right_symbol}(n2)
    """

    combined_params = {**node1_params, **node2_params, **edge_query_params}

    print(query, combined_params)
    tx.run(query, combined_params)

def upload_graph(
    tx: Transaction,
    nodes: Dict[str, Node],
    edges: Dict[str, Edge]
) -> None:

    # Create nodes first so that we can reuse them
    # when we create the relationships
    for nid, node in tqdm(nodes.items(), "Nodes"):
        create_node(tx, node)

    for eid, edge in tqdm(edges.items(), "Edges"):
        match = EDGE_REGEX.match(eid)

        if match is None:
            raise Exception(
                f"Edge '{eid}' does not seem to conform to '{EDGE_REGEX.pattern}'"
            )

        left_nid = match.group(1)
        right_nid = match.group(3)

        for nid in (left_nid, right_nid):
            if nid not in nodes:
                raise Exception(
                    f"Edge '{eid}' uses node '{nid}' which cannot be found in the nodes"
                )

        create_edge(
            tx,
            nodes[left_nid],
            nodes[right_nid],
            edge,
            DIRECTION_NAME_TABLE[match.group(2)]
        )

def main():
    from argparse import ArgumentParser, FileType

    import json

    parser = ArgumentParser()
    parser.add_argument(       "--host",                   type=str, required=True)
    parser.add_argument("-p",  "--port",                   type=int, default=7687)
    parser.add_argument("-u",  "--user",                   type=str, required=True)
    parser.add_argument("-pw", "--password",               type=str, required=True)
    parser.add_argument("-d",  "--database",               type=str, default="neo4j")
    parser.add_argument("-f",  "--file",                   type=FileType("r"), required=True)
    parser.add_argument(       "--no-prior-clear",         dest="clear", action="store_false")

    args = parser.parse_args()

    model = json.load(args.file)
    nodes = {nid: Node(**data) for nid, data in model.get("nodes", {}).items()}
    edges = {eid: Edge(**data) for eid, data in model.get("edges", {}).items()}


    uri = f"neo4j://{args.host}:{args.port}"
    auth = (args.user, args.password)
    with GraphDatabase.driver(uri, auth=auth) as driver:
        with driver.session(database=args.database) as sess:
            tx = sess.begin_transaction()

            try:
                if args.clear:
                    tx.run("MATCH (a)-[e]-(b) DELETE e;")
                    tx.run("MATCH (n) DELETE n;")

                upload_graph(tx, nodes, edges)

            except Exception as ex:
                tx.rollback()

                print(ex, file=sys.stderr)
                sys.exit(1)

            tx.commit()



if __name__ == "__main__":
    main()

