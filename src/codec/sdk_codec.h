// sdk_codec.h
// Copyright (C) 2017 4paradigm.com
// Author denglong
// Date 2020-06-10
//
#pragma once

#include <map>
#include <string>
#include <utility>
#include <vector>
#include <memory>

#include "codec/schema_codec.h"
#include "proto/common.pb.h"
#include "proto/tablet.pb.h"

namespace rtidb {
namespace codec {

using Index = google::protobuf::RepeatedPtrField<::rtidb::common::ColumnKey>;
using Dimension = std::vector<std::pair<std::string, uint32_t>>;
using Schema = google::protobuf::RepeatedPtrField<rtidb::common::ColumnDesc>;

class SDKCodec {
 public:
    explicit SDKCodec(const ::rtidb::nameserver::TableInfo& table_info);

    explicit SDKCodec(const ::rtidb::api::TableMeta& table_info);

    int EncodeDimension(const std::map<std::string, std::string>& raw_data,
                        uint32_t pid_num,
                        std::map<uint32_t, Dimension>* dimensions);

    int EncodeDimension(const std::vector<std::string>& raw_data,
                        uint32_t pid_num,
                        std::map<uint32_t, Dimension>* dimensions);

    int EncodeTsDimension(const std::vector<std::string>& raw_data,
                          std::vector<uint64_t>* ts_dimensions);

    int EncodeRow(const std::vector<std::string>& raw_data, std::string* row);

    int DecodeRow(const std::string& row, std::vector<std::string>* value);

    int CombinePartitionKey(const std::vector<std::string>& raw_data,
                            std::string* key);

    inline bool HasTSCol() const { return !ts_idx_.empty(); }

    std::vector<std::string> GetColNames();

 private:
    void ParseColumnDesc(const Schema& column_desc);
    void ParseAddedColumnDesc(const Schema& column_desc);

 private:
    Schema schema_;
    Index index_;
    std::vector<::rtidb::codec::ColumnDesc> old_schema_;
    std::map<std::string, uint32_t> schema_idx_map_;
    std::vector<uint32_t> ts_idx_;
    std::vector<uint32_t> partition_col_idx_;
    uint32_t format_version_;
    uint32_t base_schema_size_;
    int modify_times_;
    std::map<int32_t, std::shared_ptr<Schema>> version_schema_;
    int32_t last_ver_;
};

}  // namespace codec
}  // namespace rtidb
