# Routing Protocol Implementation

Implements Distance Vector (DV) and Link State (LS) routing protocols.

## Files
- `DVrouter.py` - Distance Vector implementation (Bellman-Ford)
- `LSrouter.py` - Link State implementation (Dijkstra)
- `*.json` - Network test configurations

## Running Tests

```bash
# Test all
./test_scripts/test_dv_ls.sh

# Test specific protocol
./test_scripts/test_dv_ls.sh LS
./test_scripts/test_dv_ls.sh DV

# Test individual network
python network.py 01_small_net.json LS
```

## Test Results
- **LSrouter.py**: ✅ 6/6 tests pass
- **DVrouter.py**: ✅ 4/6 tests pass

## Git Setup & Push

```bash
# Initialize and setup
git init
git remote add origin https://github.com/username/routing-protocol.git

# Commit and push
git add .
git commit -m "Implement DV and LS routing protocols"
git push -u origin main

# Tag submission
git tag -a submission -m "Final Submission"
git push --tags
```

## Implementation Notes
- **DVrouter**: Uses Bellman-Ford with split horizon and poison reverse
- **LSrouter**: Uses Dijkstra with link state flooding and sequence numbers
- Both handle link failures, additions, and periodic updates
- Fixed packet forwarding for directly connected clients


