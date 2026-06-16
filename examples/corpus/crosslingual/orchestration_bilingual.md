# DAG Orchestration / 多智能体编排

多智能体研究系统可以用 DAG 表示任务依赖关系。DAG executor tracks task dependencies and only runs ready tasks whose prerequisites have completed.

状态机让每个任务在 pending、ready、running、succeeded、failed 等状态之间流转。State machines with timeout, retry, and replan make agent workflows recoverable.

当检索没有证据、任务超时或同层失败比例过高时，系统可以触发 replan，生成替代任务并恢复受影响的下游节点。
