# Paypal importer

An importer for Paypal. Handles currency coversions and direct bank transfers.

## How to use
Please set your language to 'English' (currently the only supported language but I would be very happy with a PR) and enable the following csv entries:

- Transaction details - PayPal Balance
- Transaction details - Subject

In order to automatically set entries, you can extend the class and use the finalize method. However, you should be careful. Finalizing happens before transaction merging, so you will see more transactions in some cases. Example that works:

```python
class Importer(importer.Importer):
    def finalize(self, txn, row):
        if row.payee == "Movie Distributor":
            txn.postings[0] = txn.postings[0]._replace(
                account="Expenses:Movies"
            )
        return txn
```

## Contribution

This code is mainly for my own use and as such it is unlikely to fit all use cases yet. However, if you have an example that produces wrong output or an improvement, let me know. I think the main hurdle is having enough examples to test.
