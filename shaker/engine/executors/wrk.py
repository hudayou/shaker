# Copyright © 2017 Jacky Hu <hudayou@hotmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from hdrh.histogram import HdrHistogram

from shaker.engine.executors import base


def convert_rx_bps_to_number(rx_bps):
    multiplier = 1024.0
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    for index, unit in enumerate(units[::-1]):
        if rx_bps.endswith(unit):
            sup = len(units) - index - 1
            try:
                return float(rx_bps.strip(unit)) * multiplier ** sup
            except:
                return 0.0
    return 0.0


class WrkExecutor(base.BaseExecutor):
    def get_command(self):
        cmd = base.CommandLine('wrk')
        cmd.add('-D', self.test_definition.get('digits') or 3)
        cmd.add('-c', self.test_definition.get('connections') or 10)
        cmd.add('-d', self.test_definition.get('time') or 60)
        cmd.add('-t', self.test_definition.get('threads') or 2)
        cmd.add('-R', self.test_definition.get('rate') or 10)
        cmd.add('-p', self.test_definition.get('interval') or 1)
        cmd.add('-e')
        cmd.add('{0}://{1}'.format(self.test_definition.get('protocol') or
                                   'http',
                                   self.test_definition.get('host') or
                                   self.agent['slave']['ip']))
        return cmd.make()

    def process_reply(self, message):
        result = super(WrkExecutor, self).process_reply(message)

        stdout = result['stdout']
        if not stdout:
            raise base.ExecutorException(
                result,
                'wrk returned no data, stderr: %s' % result['stderr'])

        data = json.loads(stdout)

        meta = [
            ['time', 's'],
            ['latency', 'ms'],
            ['rps', 'req/s'],
        ]
        samples = []
        interval = self.test_definition.get('interval') or 1
        for i, d in enumerate(data):
            line = [interval * i]
            h = HdrHistogram.decode(data[i].get(
                'hist',
                'HISTFAAAABh4nJNpmSzMgABMUJoRTJq9a4DxAUGXAu8='
            ))
            line.append(h.get_mean_value()/1000.0)
            line.append(data[i].get('rps', 0.0))
            samples.append(line)

        result['meta'] = meta
        result['samples'] = samples

        return result
