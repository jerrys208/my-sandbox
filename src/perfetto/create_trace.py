import logging
from random import randint
from protos.perfetto.trace import trace_pb2
from protos.perfetto.trace.track_event import track_event_pb2
from protos.perfetto.trace.track_event import track_descriptor_pb2
from protos.perfetto.common import android_log_constants_pb2
from protos.perfetto.trace.android import android_log_pb2


from typing import List


class TracePacket(object):
    """
    * trusted_packet_sequence_id
        * https://github.com/google/perfetto/issues/124
        * 1 sequence = 1 stream of packets from a thread
        * remember to set SEQ_INCREMENTAL_STATE_CLEARED on the first packet for each sequence,
    * android log
        * https://github.com/google/perfetto/issues/640
        * https://github.com/google/perfetto/issues/507
    """

    def __init__(self):
        self.root = trace_pb2.Trace()
        self.uuid: int = 0

        clock_snapshot = self.root.packet.add()
        clock_snapshot.clock_snapshot.clocks.add(
            clock_id=1,
            timestamp=1667845191015992418,
        )
        clock_snapshot.clock_snapshot.clocks.add(
            clock_id=2,
            timestamp=1667845191012001939,
        )
        clock_snapshot.clock_snapshot.clocks.add(
            clock_id=3,
            timestamp=3973373760321,
        )
        clock_snapshot.clock_snapshot.clocks.add(
            clock_id=4,
            timestamp=3973369769802,
        )
        clock_snapshot.clock_snapshot.clocks.add(
            clock_id=5,
            timestamp=3973373760484,
        )
        clock_snapshot.clock_snapshot.clocks.add(
            clock_id=6,
            timestamp=3973373760037,
        )

    def get_next_id(self) -> int:
        self.uuid += 1
        return self.uuid

    def save_to_file(self, filename: str):
        with open(filename, 'wb') as out:
            out.write(self.root.SerializeToString())

    @classmethod
    def decode_trace_file(cls, filename: str):
        with open(filename, 'rb') as src:
            trace_data = src.read()
        trace = trace_pb2.Trace()
        trace.ParseFromString(trace_data)
        for packet in trace.packet:
            if packet.HasField('clock_snapshot'):
                logging.info(f'[*] {packet}')
            # if packet.HasField("android_log_packet"):
            #     print("Found AndroidLogPacket:")
            #     for event in packet.android_log_packet.log_events:
            #         print(f"Tag: {event.tag}, Message: {event.message}")

    ############################################################
    # android log

    def add_android_log(self, time_us: int, text: str):
        packet = self.root.packet.add()
        packet.timestamp = time_us * 1000
        packet.trusted_packet_sequence_id = 1  # 信任序列
        # log
        # events
        evt = packet.android_log.events.add()
        evt.log_id = android_log_constants_pb2.AndroidLogId.LID_RADIO
        evt.pid = 100
        evt.tid = 200
        evt.uid = 400
        evt.timestamp = 3956926228716
        # 3956926228716
        # 3979274976796
        evt.tag = 'my_tag'
        evt.message = text
        evt.prio = android_log_constants_pb2.AndroidLogPriority.PRIO_INFO
        # stat
        stat = packet.android_log.stats     # android_log_pb2.AndroidLogPacket.Stats
        stat.num_total = 1
        stat.num_failed = 0
        stat.num_skipped = 0

    ############################################################
    # track_event

    def add_instant_track_event(self, track_id: int, name: str, time_us: int):
        # TYPE_INSTANT
        inst_event = self.root.packet.add()
        inst_event.timestamp = time_us * 1000
        inst_event.trusted_packet_sequence_id = 1  # 信任序列
        inst_event.track_event.type = track_event_pb2.TrackEvent.Type.TYPE_INSTANT
        inst_event.track_event.name = name
        inst_event.track_event.track_uuid = track_id  # 將 Track 綁定到同一層
        inst_event.track_event.log_message.body_iid = 1
        inst_event.track_event.log_message.source_location_iid = 3
        msg = inst_event.interned_data.log_message_body.add()
        msg.iid = 1
        msg.body = 'message for log test'
        src = inst_event.interned_data.source_locations.add()
        src.iid = 3
        src.function_name = 'func_abc'
        src.file_name = 'func.cc'
        src.line_number = 111

    def add_slice_track_event(
            self, track_id: int, name: str, beg_time_us: int, end_time_us: int, categories: List[str] = None):
        # 開始事件 (TYPE_SLICE_BEGIN)
        beg_pkt = self.root.packet.add()
        beg_pkt.timestamp = beg_time_us * 1000
        beg_pkt.trusted_packet_sequence_id = 1  # 信任序列
        beg_pkt.track_event.type = track_event_pb2.TrackEvent.Type.TYPE_SLICE_BEGIN
        beg_pkt.track_event.name = name
        if categories:
            for category in categories:
                beg_pkt.track_event.categories.append(category)
        beg_pkt.track_event.track_uuid = track_id  # 將 Track 綁定到同一層
        # beg_pkt.track_event.flow_ids.append(1055895987)

        # 添加自定義延遲信息到 debug_annotations
        for idx in range(5):
            annotation = beg_pkt.track_event.debug_annotations.add()
            annotation.name = f'log_{idx}'
            annotation.string_value = '原始的 log text'

        # 結束事件 (TYPE_SLICE_END)
        end_event = self.root.packet.add()
        end_event.timestamp = end_time_us * 1000
        end_event.trusted_packet_sequence_id = 1
        end_event.track_event.type = track_event_pb2.TrackEvent.Type.TYPE_SLICE_END
        end_event.track_event.track_uuid = track_id


    ############################################################
    # track_descriptor
    def add_track_descriptor(self, name: str, parent_uuid: int = None):
        packet = self.root.packet.add()
        packet.track_descriptor.name = name
        packet.track_descriptor.uuid = self.get_next_id()
        if parent_uuid:
            packet.track_descriptor.parent_uuid = parent_uuid
        return packet

    def add_process_track_descriptor(self, name: str, pid: int):
        packet = self.add_track_descriptor(name)
        packet.track_descriptor.process.pid = pid
        packet.track_descriptor.process.process_name = name
        return packet

    def add_thread_track_descriptor(self, name: str, pid: int, tid: int):
        packet = self.add_track_descriptor(name)
        packet.track_descriptor.thread.pid = pid
        packet.track_descriptor.thread.tid = tid
        packet.track_descriptor.thread.thread_name = name
        return packet


def create_trace_2():
    trace = TracePacket()
    trace.add_process_track_descriptor('process-1', 100)
    packet = trace.add_thread_track_descriptor('thread-1', 100, 200)
    track_id = packet.track_descriptor.uuid
    trace.add_slice_track_event(track_id, 'event-1', 1734138868 * 1000000, (1734138868 + 5) * 1000000)
    trace.add_slice_track_event(track_id, 'event-2', 1734138878 * 1000000, (1734138878 + 5) * 1000000)

    pkt = trace.add_track_descriptor('Android Logs')
    pkt.trusted_packet_sequence_id = 1  # 必需的唯一 ID
    pkt.incremental_state_cleared = True
    # trace.add_instant_track_event(pkt.track_descriptor.uuid, '事件', 1734138870 * 1000000)

    trace.add_android_log(1734138868 * 1000000, 'test log text from my custom')
    # trace.add_android_log(1734138869 * 1000000, 'test log text from my custom')
    # trace.add_android_log(1734138870 * 1000000, 'test log text from my custom')

    # save to file
    trace.save_to_file('trace_test.pb')
    trace.decode_trace_file('trace_test.pb')
    return trace


def create_trace(data):
    trace = trace_pb2.Trace()

    # 添加時間基準 (ClockSnapshot)
    clock_snapshot = trace.packet.add()
    clock_snapshot.clock_snapshot.clocks.add(
        clock_id=1,  # 默認時鐘 ID
        timestamp=0  # 設置為 0 表示基準時間
    )

    # Track 的唯一 ID
    track_id = 1

    # TYPE_INSTANT
    inst_event = trace.packet.add()
    inst_event.timestamp = 1050 * 1000  # 微秒
    inst_event.trusted_packet_sequence_id = 1  # 信任序列
    inst_event.track_event.type = track_event_pb2.TrackEvent.Type.TYPE_INSTANT
    inst_event.track_event.name = '事件'
    inst_event.track_event.track_uuid = track_id  # 將 Track 綁定到同一層
    track_id += 1

    # track_descriptor for process & thread
    proc_event = trace.packet.add()
    proc_event.track_descriptor.name = 'my_proc'
    proc_event.track_descriptor.uuid = 894893984
    proc_event.track_descriptor.process.pid = 1111
    proc_event.track_descriptor.process.process_name = 'AABBC'
    thrd_event = trace.packet.add()
    thrd_event.track_descriptor.name = 'my_thread'
    thrd_event.track_descriptor.uuid = 49083589894
    thrd_event.track_descriptor.thread.pid = 1111
    thrd_event.track_descriptor.thread.tid = 2222
    thrd_event.track_descriptor.thread.thread_name = 'MyThread'

    # counter
    cntr_event = trace.packet.add()
    cntr_event.track_descriptor.uuid = 4489498
    cntr_event.track_descriptor.parent_uuid = 894893984
    cntr_event.track_descriptor.name = 'cpu_counter'
    cntr_event.track_descriptor.counter.unit_name = 'xx'

    # 為每個數據點添加事件
    for idx, entry in enumerate(data):
        track_id = 49083589894

        # counter
        counter_event = trace.packet.add()
        counter_event.timestamp = entry["timestamp"] * 1000  # 微秒
        counter_event.trusted_packet_sequence_id = 3903809  # 信任序列
        counter_event.track_event.type = track_event_pb2.TrackEvent.Type.TYPE_COUNTER
        counter_event.track_event.track_uuid = 4489498
        counter_event.track_event.counter_value = randint(1000, 5000)

        # 開始事件 (TYPE_SLICE_BEGIN)
        begin_event = trace.packet.add()
        begin_event.timestamp = entry["timestamp"] * 1000  # 微秒
        begin_event.trusted_packet_sequence_id = 1  # 信任序列
        begin_event.track_event.type = track_event_pb2.TrackEvent.Type.TYPE_SLICE_BEGIN
        begin_event.track_event.name = entry["layer"]  # 層級名稱
        begin_event.track_event.categories.append('C1')
        begin_event.track_event.track_uuid = track_id  # 將 Track 綁定到同一層
        begin_event.track_event.flow_ids.append(1055895987)

        # 添加自定義延遲信息到 debug_annotations
        annotation = begin_event.track_event.debug_annotations.add()
        annotation.name = "delay_ms"
        annotation.int_value = entry["delay"]

        # 結束事件 (TYPE_SLICE_END)
        end_event = trace.packet.add()
        end_event.timestamp = (entry["timestamp"] + entry["delay"]) * 1000  # 結束時間 = 開始時間 + 延遲
        end_event.trusted_packet_sequence_id = 1
        end_event.track_event.type = track_event_pb2.TrackEvent.Type.TYPE_SLICE_END
        end_event.track_event.track_uuid = track_id

        # 遞增 Track ID 用於區分事件
        track_id += 1

    return trace


# 模擬數據
data = []
name_list = ['Application', 'Transport', 'Network']

for i in range(20):
    layer = name_list[i%3]
    data.append({"timestamp": (1000 + i*50), "layer": layer, "delay": randint(30, 100)})

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    create_trace_2()

    print("Trace file saved: network_trace.pb")
