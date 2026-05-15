# V6 Experiment Pseudocode

```text
Input:
  Vehicle counts C = {5, 10, 15, 20}
  Repetitions R = 5
  Emergency vehicle = sta1
  Helpers = all other vehicles
  Emergency UDP rate = 10 Mbit/s
  Aggregate helper UDP rate = 10 Mbit/s
  Aggregate helper TCP offered load = 80 Mbit/s
  SDNV helper TCP cap after trigger = 10 Mbit/s
  Warm-up = 10 s
  Measurement duration = 60 s

for each vehicle count c in C do
    deploy topology with c vehicles in a 1000 x 1000 m area
    assign sta1 as emergency vehicle
    assign remaining c-1 vehicles as helpers

    for repetition r from 1 to R do
        for scenario s in {baseline, sdnv} do
            start SDN controller
            instantiate Mininet-WiFi topology
            apply common pre-trigger shaping and start background traffic
            wait for warm-up interval

            trigger emergency communication mode

            if s == baseline then
                keep flat helper policy
                allow emergency UDP + helper UDP + helper TCP to coexist
            else if s == sdnv then
                prioritize emergency UDP at the emergency vehicle
                prioritize cooperative helper UDP at helper vehicles
                throttle aggregate helper TCP to the SDNV cap
            end if

            during the measurement interval do
                record emergency UDP latency
                record background TCP latency
                record primary emergency UDP throughput
                record helper UDP throughput
                record background TCP throughput
                record policy reaction time (SDNV only)
                record priority enforcement ratio
                record UDP share and traffic suppression efficiency
            end during

            run EMAPT dissemination measurement:
                transmit emergency awareness message from sta1
                measure notification completion times at all helper vehicles
                compute EMAPT-50, EMAPT-90, EMAPT-100

            stop topology and collect logs
        end for
    end for
end for

Aggregate all repetitions:
  compute mean and standard deviation for every metric
  generate latency, throughput, and EMAPT plots versus vehicle count
```
