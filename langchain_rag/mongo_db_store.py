from datetime import datetime, UTC
from typing import Iterable, Optional

from langgraph.store.base import BaseStore, Op, Result, Item, PutOp, GetOp
from pymongo import MongoClient


class MongoDBStore(BaseStore):
    def __init__(self, mongo_client: MongoClient, db_name: str, collection_name: str):
        self.mongo_client = mongo_client
        self.db_name = db_name
        self.collection_name = collection_name

        self.collection = self.mongo_client[self.db_name][self.collection_name]

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        raise NotImplementedError

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        results = []
        for op in ops:
            if isinstance(op, PutOp):
                result = self._put(op)
            elif isinstance(op, GetOp):
                result = self._get(op)
            else:
                raise NotImplementedError(f"Operation {type(op)} not supported")
            results.append(result)
        return results

    def _put(self, op: PutOp) -> None:
        doc = {
            "namespace": op.namespace,
            "key": op.key,
            "value": op.value,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        if op.value is None:  # Delete if value is None
            self.collection.delete_one({"namespace": op.namespace, "key": op.key})
        else:
            self.collection.update_one(
                {"namespace": op.namespace, "key": op.key},
                {"$set": doc},
                upsert=True,
            )

    def _get(self, op: GetOp) -> Optional[Item]:
        result = self.collection.find_one({"namespace": op.namespace, "key": op.key})
        if result:
            return Item(
                namespace=result["namespace"],
                key=result["key"],
                value=result["value"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )
        return None
