---
applyTo: '**'
---
# Project Rules & info

## Important
- No mock, fake or hardcoded data prohibited including
- Do not keep or create files having same or similar role
- Make sure you obey the architecture and file structure
- If you created a temporary file to test a feature make sure you deleted after usage
- Before creating the file make sure you are putting that file into where it belongs according to file structure
- No fallbacks, code as intended. Should fail sometimes so we can see errors to fix
- No inline/embedded/hardcoded file creation
- Policy Engine is the hearth: If anything related to the Policy Engine needs fix first try to match the component architecture with policy engine architecture instead of trying to modify Policy Engine.
- Do not use terminal to create files using terminal. Use IDE to create files and folders.
## Project Specific Rules
- Ensure every component checking in with and following rules in the PolicyEngine to operate

## Configs
We are using `configs` directory to store config

## Scenarios
- We are using scenario classes derive new classes to simulate real life scenarios.
- We are trying to create challanges in the scenarios with the network to see results
- Scenarios should be as realistic as possible maybe more harsh by adjusting network parameters: bandwith, packet loss, bad nodes etc. 


## GNS3 Network
- We have running GNS3 remote server, which can run docker containers
- Use SDN with OpenFlow switches

### GNS3 Nodes 
- Each system component have its own image pushed to `abdulmelink` registry at docker hub.
- We need to use images at `abdulmelink` to create GNS3 node templates for nodes
- We need to get logs and metrics from the component running on docker node.
- Check `docker/` directory for dockerfiles

