# Activity Diagrams & Sequence Diagrams
## Team Member: Katlego

## Activity Diagrams
### Main Simulation Activity Flow:
[Start Simulation] → [Validate Parameters] → [Check Resource Limits]
→ [Launch Attack Threads] → [Monitor Resources] → [Update GUI]
→ [Log Metrics] → [Cleanup Resources] → [Generate Report] → [End]



### Attack Configuration Activity:
[Select Attack Type] → [Set Parameters] → [Validate Inputs]
→ [Save Configuration] → [Update UI Components]



## Sequence Diagrams
### Simulation Startup Sequence:
1. User → GUI: Click "Start Attack"
2. GUI → SafetyManager: Check resource limits
3. SafetyManager → GUI: Approval response
4. GUI → AttackFactory: Create attack instance
5. AttackFactory → SimulationEngine: Initialize simulation
6. SimulationEngine → ThreadManager: Launch worker threads

### Real-time Monitoring Sequence:
1. ThreadManager → AttackThread: Execute attack simulation
2. AttackThread → DataLogger: Send metrics
3. DataLogger → GUI: Update statistics
4. GUI → GraphRenderer: Update visualization
