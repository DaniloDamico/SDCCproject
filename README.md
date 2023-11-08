# Project B2: FaaS management

- Manage single functions written in a given programming
  language inside a container
- Offload to Cloud according to a local decision policy
- Deployment using Docker or another container engine (e.g.,
  Podman, Firecracker) and AWS Lambda for function
  offloading

### Details
- System/service with configurable parameters through a configuration file/service
- System/service state should be distributed. The only allowed centralized service can be one that
supports service discovery, users logging, and other housekeeping tasks
- System/service supports multiple, autonomous
entities which may contend for shared resources
- System/service supports update to some form of
shared state.
    - System/service scalability and elasticity
    - System/service fault tolerance
- In particular, system/service continues operation even if one of
the participant nodes crashes (optionally, it recovers the state of
a crashed node so that it can resume operation)