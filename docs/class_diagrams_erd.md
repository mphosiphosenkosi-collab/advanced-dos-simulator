# Class Diagrams & ERD Extensions
## Team Member: Gift

## Class Diagram Structure
### Core Classes:
1. **DoSSimulatorApp** (Main Application Class)
   - Properties: config, monitor, logger, attack_threads
   - Methods: start_simulation(), stop_simulation(), update_gui()

2. **AttackFactory** (Factory Pattern)
   - Methods: create_attack(attack_type)

3. **BaseAttack** (Abstract Base Class)
   - Properties: attack_id, intensity, duration
   - Methods: simulate(), validate_safety()

4. **ResourceMonitor** (Singleton Pattern)
   - Properties: cpu_threshold, memory_threshold
   - Methods: monitor_resources(), check_limits()

## ERD Extensions (SQLite Database)
### Additional Tables:
1. **educational_content** - Attack explanations and mitigations
2. **user_sessions** - User interaction tracking
3. **system_metrics** - Performance monitoring data

### Table Relationships:
- simulations ↔ attack_metrics (One-to-Many)
- simulations ↔ educational_content (Many-to-One)
