# PyFlood
Script for generating network traffic.

## Usage:
```shell
main.py [-h] [-host HOST] [-cfg CONFIG] [-m {dns,http,rhttp,rshttp,tcp,udp}] [-t THREADS] [-url URL] [-norcv]
        [-msg MESSAGE] [-thr THROTTLE] [-timeout TIMEOUT] [-proxy PROXY] [-rpc RPC]
        [-cookie COOKIE] [-useragent USERAGENT]
```

### Methods:
* `udp`: Send message or random bytes to udp socket
* `tcp`: Send message or random bytes to tcp socket
* `dns`: Dns request with random or Url domain
* `http`: Http request
* `httpr`: Http request with `requests` module

### JSON Config file:
Object that redefine parameters. `Jobs` - parameters-array per job. 
#### Note:
* From array-type parameter will be chosen random variant.
* String can contains template expression: `{ParamName}`. Embedded parameters name start with capital. See help `main.py -h` 
```json
{
  "ParamNameA": "String value A: {ParamNameB}",
  "ParamNameB": ["String value AA", "String value BB"],
  "ParamNameC": 4,
  ...
  "Jobs": [
    {
      "ParamNameA": "String value B: {ParamNameB}", 
      "ParamNameB": ["String value AAA", "String value BBB"],
      "ParamNameC": 8,
      ...
    },
    ...
  ]
}
```

### Parameters override priority:
* `_default.json`
* Command line parameters
* File in `-cfg` parameter, default is `_<method_name>.json`

### Output:
`[<method>]<host> x<threads> TX:<transfer size speed>|<request/s> RX:<receive size> F:<failed count> <last error>`
