## Product Requirement Document

Hey team, we need to build out the secret state management thing we discussed last sprint. Basically, clients need isolated storage for sensitive stuff — like secrets, keys, signing material — and we need to make sure none of the raw secret bytes are ever exposed in any output. Think of it as similar to what we did with the session isolation logic in the old auth module, but more structured this time.

The system should support writing indexed records into named vaults per client, removing records, and also doing a full garbage collection pass. There's also a need for a separate non-secret key/value store that works independently of the vault. Persistence is important — we should be able to save all state into a named encrypted snapshot and reload it later after wiping the in-memory state.

On the crypto side, we need hashing, signing with hierarchical key derivation, key agreement, authenticated encryption, and BIP39 recovery flows. All crypto outputs should be in lowercase hex, and the operations need to be deterministic given fixed inputs. The hint listing order for vault records is deterministic but not sorted in any obvious way, so devs are going to need to match the internal storage order exactly.

Multiple clients need to be fully isolated even when targeting the same vault path. Client lifecycle stuff (spawn, switch, remove, retarget) should produce proper error categories, not raw exceptions. Let's make this clean and production-grade.