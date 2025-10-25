# Use Case Diagrams & Component Diagrams
## Team Member: David

## Use Case Diagrams
### Primary Use Cases:
1. **Simulate DoS Attack**
   - Actor: Educator/Student
   - Description: User configures and runs a DoS attack simulation
   - Preconditions: Application launched, parameters set
   - Postconditions: Simulation data saved, resources released

2. **View Attack Analytics**
   - Actor: Educator/Student  
   - Description: User views historical simulation data and graphs
   - Preconditions: Previous simulations exist
   - Postconditions: Data displayed/exported

3. **Configure Safety Limits**
   - Actor: Educator
   - Description: Set resource usage limits for simulations
   - Preconditions: Admin/educator privileges
   - Postconditions: Safety limits applied to all simulations

## Component Diagrams
### System Components:
1. **GUI Layer** - Tkinter interface
2. **Simulation Engine** - Attack simulation logic
3. **Data Management** - Logging and storage
4. **Safety Manager** - Resource monitoring
5. **Visualization** - Graph and chart rendering

### Component Interactions:
- GUI ↔ Simulation Engine (start/stop commands)
- Simulation Engine ↔ Data Management (log storage)
- Safety Manager ↔ All components (resource monitoring)
