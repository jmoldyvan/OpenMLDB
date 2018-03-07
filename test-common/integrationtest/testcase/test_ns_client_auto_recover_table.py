# -*- coding: utf-8 -*-
from testcasebase import TestCaseBase
import time
import os
from libs.test_loader import load
import libs.utils as utils
from libs.logger import infoLogger
from libs.deco import multi_dimension
import libs.ddt as ddt

@ddt.ddt
class TestAutoRecoverTable(TestCaseBase):

    def confset_createtable_put(self):
        self.confset(self.ns_leader, 'auto_failover', 'true')
        self.confset(self.ns_leader, 'auto_recover_table', 'true')
        self.tname = 'tname{}'.format(time.time())
        metadata_path = '{}/metadata.txt'.format(self.testpath)
        m = utils.gen_table_metadata(
            '"{}"'.format(self.tname), '"kAbsoluteTime"', 144000, 8,
            ('table_partition', '"{}"'.format(self.leader), '"0-3"', 'true'),
            ('table_partition', '"{}"'.format(self.slave1), '"0-3"', 'false'),
            ('table_partition', '"{}"'.format(self.slave2), '"2-3"', 'false'),
            ('column_desc', '"k1"', '"string"', 'true'),
            ('column_desc', '"k2"', '"string"', 'false'),
            ('column_desc', '"k3"', '"string"', 'false'))
        utils.gen_table_metadata_file(m, metadata_path)
        rs = self.ns_create(self.ns_leader, metadata_path)
        self.assertEqual('Create table ok' in rs, True)
        table_info = self.showtable(self.ns_leader)
        self.tid = int(table_info.keys()[0][1])
        self.pid = 3
        for _ in range(10):
            self.put(self.leader, self.tid, self.pid, 'testkey0', self.now() + 90000, 'testvalue0')


    def get_latest_op(self):
        rs = self.showopstatus(self.ns_leader)
        latest_ley = max(rs.keys())
        return latest_ley, rs[latest_ley][0]


    def get_task_dict(self, tname):
        opid_rs = utils.exe_shell("grep -a {} {}/info.log|grep op_id|grep \"name\[\""
                                  "|sed 's/\(.*\)op_id\[\(.*\)\] name\(.*\)/\\2/g'".format(tname, self.ns_leader_path))
        opid_x = opid_rs.split('\n')
        task_dict = {}
        for opid in opid_x:
            cmd = "cat {}/info.log |grep \"op_id\[{}\]\"|grep task_type".format(self.ns_leader_path, opid) \
                  + "|awk -F '\\\\[' '{print $4\"]\"$5\"]\"$6}'" \
                    "|awk -F '\\\\]' '{print $1\",\"$3\",\"$5}'"
            infoLogger.info(cmd)
            rs = utils.exe_shell(cmd).split('\n')
            infoLogger.info(rs)
            for x in rs:
                x = x.split(',')
                task_dict[(int(x[1]), x[2])] = x[0]
        self.task_dict = task_dict


    def put_data(self, endpoint):
        rs = self.put(endpoint, self.tid, self.pid, "testkey0", self.now() + 1000, "testvalue0")
        self.assertEqual("ok" in rs, True)


    def check_tasks(self, op_id, *args):
        self.get_task_dict(self.tname)
        tasks = [k[1] for k, v in self.task_dict.items() if k[0] == op_id and v == 'kDone']
        infoLogger.info(self.task_dict)
        infoLogger.info(op_id)
        infoLogger.info(tasks)
        infoLogger.info(args)
        self.assertEqual(set(args) - set(tasks), set([]))


    def check_re_add_replica_op(self):
        op_id = self.get_latest_op()[0]
        self.check_tasks(op_id,
                         'kPauseSnapshot',
                         'kSendSnapshot',
                         'kLoadTable',
                         'kRecoverSnapshot',
                         'kAddReplica')


    def check_re_add_replica_no_send_op(self):
        op_id = self.get_latest_op()[0]
        self.check_tasks(op_id,
                         'kPauseSnapshot',
                         'kLoadTable',
                         'kRecoverSnapshot',
                         'kAddReplica')


    def check_re_add_replica_with_drop_op(self):
        op_id = self.get_latest_op()[0]
        self.check_tasks(op_id,
                         'kPauseSnapshot',
                         'kSendSnapshot',
                         'kLoadTable',
                         'kDropTable',
                         'kRecoverSnapshot',
                         'kAddReplica')


    def check_re_add_replica_simplify_op(self):
        op_id = self.get_latest_op()[0]
        self.check_tasks(op_id, 'kAddReplica')


    @staticmethod
    def get_steps_dict():
        return {
            0: 'time.sleep(10)',
            1: 'self.confset_createtable_put()',
            2: 'self.stop_client(self.leader)',
            3: 'self.disconnectzk(self.leader)',
            4: 'self.stop_client(self.slave1)',
            5: 'self.disconnectzk(self.slave1)',
            6: 'self.find_new_tb_leader(self.tname, self.tid, self.pid)',
            7: 'self.put_data(self.leader)',
            8: 'self.put_data(self.new_tb_leader)',
            9: 'self.confset(self.ns_leader, "auto_recover_table", "false")',
            10: 'self.makesnapshot(self.leader, self.tid, self.pid)',
            11: 'self.makesnapshot(self.slave1, self.tid, self.pid), self.makesnapshot(self.slave2, self.tid, self.pid)',
            12: 'self.makesnapshot(self.ns_leader, self.tname, self.pid, \'ns_client\')',
            13: 'self.start_client(self.leaderpath)',
            14: 'self.start_client(self.slave1path)',
            15: 'self.connectzk(self.leader)',
            16: 'self.connectzk(self.slave1)',
            17: 'self.assertEqual(self.get_latest_op()[1], "kReAddReplicaOP")',
            18: 'self.assertEqual(self.get_latest_op()[1], "kReAddReplicaNoSendOP")',
            19: 'self.assertEqual(self.get_latest_op()[1], "kReAddReplicaWithDropOP")',
            20: 'self.assertEqual(self.get_latest_op()[1], "kReAddReplicaSimplifyOP")',
            21: 'self.check_re_add_replica_op()',
            22: 'self.check_re_add_replica_no_send_op()',
            23: 'self.check_re_add_replica_with_drop_op()',
            24: 'self.check_re_add_replica_simplify_op()',
        }


    @ddt.data(
        (1, 3, 0, 6, 15, 0, 20, 24),  # offset = manifest.offset
        (1, 3, 0, 6, 12, 15, 0, 20),  # offset = manifest.offset
        (1, 3, 0, 6, 8, 15, 0, 20),  # offset = manifest.offset
        (1, 3, 0, 6, 8, 12, 15, 0, 19, 23),  # offset < manifest.offset
        (1, 12, 3, 0, 12, 15, 0, 20),  # offset = manifest.offset
        (1, 11, 7, 10, 3, 0, 15, 0, 20),  # offset > manifest.offset
        (1, 3, 0, 6, 7, 15, 0, 19),  # not match
        (1, 3, 0, 6, 7, 12, 15, 0, 19),  # not match
        (1, 3, 0, 6, 7, 8, 15, 0, 19),  # not match
        (1, 3, 0, 7, 10, 2, 12, 13, 0, 17),  # not match
        (1, 12, 2, 0, 6, 12, 13, 0, 18, 22),  # offset = manifest.offset
        (1, 11, 7, 10, 2, 0, 13, 0, 18),  # 12 offset > manifest.offset
        (1, 11, 7, 7, 10, 2, 0, 6, 8, 13, 0, 18),  # 13 offset > manifest.offset
        (1, 2, 0, 6, 13, 0, 17, 21),  # offset < manifest.offset
        (1, 2, 0, 6, 12, 13, 0, 17),  # offset < manifest.offset
        (1, 2, 0, 6, 8, 13, 0, 17),
        (1, 2, 0, 6, 10, 12, 13, 0, 17),
        (1, 2, 0, 6, 8, 12, 13, 0, 17),
        (1, 5, 0, 16, 0, 20),
        (1, 4, 0, 14, 0, 17),
        (1, 12, 3, 7, 2, 0, 13, 0, 18),  # RTIDB-222
    )
    @ddt.unpack
    def test_auto_recover_table(self, *steps):
        steps_dict = self.get_steps_dict()
        for i in steps:
            infoLogger.info('*' * 10 + ' Executing step {}: {}'.format(i, steps_dict[i]))
            eval(steps_dict[i])
        rs = self.showtable(self.ns_leader)
        role_x = [v[0] for k, v in rs.items()]
        is_alive_x = [v[-1] for k, v in rs.items()]

        self.assertEqual(role_x.count('leader'), 4)
        self.assertEqual(role_x.count('follower'), 6)
        self.assertEqual(is_alive_x.count('yes'), 10)
        self.assertEqual(self.get_table_status(self.leader, self.tid, self.pid)[0],
                         self.get_table_status(self.slave1, self.tid, self.pid)[0])
        self.assertEqual(self.get_table_status(self.leader, self.tid, self.pid)[0],
                         self.get_table_status(self.slave2, self.tid, self.pid)[0])


    @ddt.data(
        (1, 9, 15)
    )
    @ddt.unpack
    def test_deadlock_bug(self, *steps):
        steps_dict = self.get_steps_dict()
        for i in steps:
            eval(steps_dict[i])
        rs = self.showtable(self.ns_leader)
        self.assertEqual(self.tname in rs.keys()[0], True)


if __name__ == "__main__":
    load(TestAutoRecoverTable)
