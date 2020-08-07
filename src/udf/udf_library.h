/*-------------------------------------------------------------------------
 * Copyright (C) 2019, 4paradigm
 * udf_library.h
 *
 * Author: chenjing
 * Date: 2019/11/26
 *--------------------------------------------------------------------------
 **/
#ifndef SRC_UDF_UDF_LIBRARY_H_
#define SRC_UDF_UDF_LIBRARY_H_

#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "base/fe_status.h"
#include "node/node_manager.h"
#include "node/sql_node.h"
#include "vm/jit.h"

namespace fesql {
namespace udf {

using fesql::base::Status;
using fesql::node::ExprListNode;
using fesql::node::ExprNode;
using fesql::node::SQLNode;

// Forward declarations
class ExprUDFRegistryHelper;
class LLVMUDFRegistryHelper;
class ExternalFuncRegistryHelper;
class UDAFRegistryHelper;
class UDFTransformRegistry;
class UDAFRegistry;
class CompositeRegistry;
class UDFResolveContext;

template <template <typename> typename FTemplate>
class ExternalTemplateFuncRegistryHelper;

template <template <typename> typename FTemplate>
class CodeGenUDFTemplateRegistryHelper;

template <template <typename> typename FTemplate>
class UDAFTemplateRegistryHelper;

template <template <typename> typename FTemplate>
class ExprUDFTemplateRegistryHelper;

/**
 * Hold global udf registry entries.
 * "fn(arg0, arg1, ...argN)" -> some expression
 */
class UDFLibrary {
 public:
    Status Transform(const std::string& name,
                     const std::vector<node::ExprNode*>& args,
                     node::NodeManager* node_manager, ExprNode** result);

    Status Transform(const std::string& name, UDFResolveContext* ctx,
                     ExprNode** result);

    Status ResolveFunction(const std::string& name, UDFResolveContext* ctx,
                           node::FnDefNode** result);

    Status ResolveFunction(const std::string& name,
                           const std::vector<node::ExprNode*>& args,
                           node::NodeManager* node_manager,
                           node::FnDefNode** result);

    std::shared_ptr<UDFTransformRegistry> Find(const std::string& name) const;

    bool IsUDAF(const std::string& name, size_t args);
    void SetIsUDAF(const std::string& name, size_t args);

    // register interfaces
    ExprUDFRegistryHelper RegisterExprUDF(const std::string& name);
    LLVMUDFRegistryHelper RegisterCodeGenUDF(const std::string& name);
    ExternalFuncRegistryHelper RegisterExternal(const std::string& name);
    UDAFRegistryHelper RegisterUDAF(const std::string& name);

    Status RegisterAlias(const std::string& alias, const std::string& name);
    Status RegisterFromFile(const std::string& path);

    template <template <typename> class FTemplate>
    auto RegisterExternalTemplate(const std::string& name) {
        return ExternalTemplateFuncRegistryHelper<FTemplate>(name, this);
    }

    template <template <typename> class FTemplate>
    auto RegisterCodeGenUDFTemplate(const std::string& name) {
        return CodeGenUDFTemplateRegistryHelper<FTemplate>(name, this);
    }

    template <template <typename> class FTemplate>
    auto RegisterUDAFTemplate(const std::string& name) {
        return DoStartRegister<UDAFTemplateRegistryHelper<FTemplate>,
                               UDAFRegistry>(name);
    }

    template <template <typename> class FTemplate>
    auto RegisterExprUDFTemplate(const std::string& name) {
        return ExprUDFTemplateRegistryHelper<FTemplate>(name, this);
    }

    void AddExternalSymbol(const std::string& name, void* addr);
    void InitJITSymbols(::llvm::orc::LLJIT* jit_ptr);

    node::NodeManager* node_manager() { return &nm_; }

    const std::unordered_map<std::string, std::shared_ptr<CompositeRegistry>>&
    GetAllRegistries() {
        return table_;
    }

 private:
    template <typename Helper, typename RegistryT>
    Helper DoStartRegister(const std::string& name) {
        auto reg_item = std::make_shared<RegistryT>(name);
        InsertRegistry(reg_item);
        return Helper(reg_item, this);
    }

    void InsertRegistry(std::shared_ptr<UDFTransformRegistry> reg_item);

    std::unordered_map<std::string, std::unordered_set<size_t>> udaf_tags_;
    std::unordered_map<std::string, std::shared_ptr<CompositeRegistry>> table_;
    std::unordered_map<std::string, void*> external_symbols_;

    node::NodeManager nm_;
};

}  // namespace udf
}  // namespace fesql

#endif  // SRC_UDF_UDF_LIBRARY_H_
