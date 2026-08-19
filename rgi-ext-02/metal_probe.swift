import Foundation
import Metal

struct Probe: Codable {
    let timestamp_utc: String
    let device_name: String
    let registry_id: UInt64
    let has_unified_memory: Bool
    let max_buffer_length: UInt64
    let recommended_max_working_set_size: UInt64
    let current_allocated_size: UInt64
    let allocated_buffer_sizes: [UInt64]
    let allocation_failures: [UInt64]
    let metal_available: Bool
}

let formatter = ISO8601DateFormatter()
guard let device = MTLCreateSystemDefaultDevice() else {
    let out:[String:Any] = ["timestamp_utc": formatter.string(from: Date()), "metal_available": false]
    let data = try JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .sortedKeys])
    FileHandle.standardOutput.write(data)
    exit(2)
}

let candidateSizes:[UInt64] = [
    1 << 20, 4 << 20, 16 << 20, 64 << 20, 128 << 20,
    256 << 20, 512 << 20, 768 << 20, 1024 << 20
]
var successes:[UInt64] = []
var failures:[UInt64] = []
var buffers:[MTLBuffer] = []
for size in candidateSizes {
    autoreleasepool {
        if let b = device.makeBuffer(length: Int(size), options: .storageModeShared) {
            successes.append(size)
            buffers.append(b)
        } else {
            failures.append(size)
        }
    }
}

let probe = Probe(
    timestamp_utc: formatter.string(from: Date()),
    device_name: device.name,
    registry_id: device.registryID,
    has_unified_memory: device.hasUnifiedMemory,
    max_buffer_length: UInt64(device.maxBufferLength),
    recommended_max_working_set_size: UInt64(device.recommendedMaxWorkingSetSize),
    current_allocated_size: UInt64(device.currentAllocatedSize),
    allocated_buffer_sizes: successes,
    allocation_failures: failures,
    metal_available: true
)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
FileHandle.standardOutput.write(try encoder.encode(probe))
