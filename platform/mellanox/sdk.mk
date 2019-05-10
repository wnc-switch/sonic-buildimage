MLNX_SDK_BASE_URL = https://github.com/Mellanox/SAI-Implementation/raw/e7da154ddf8447c04b852195f43c83802c6934c9/sdk
MLNX_SDK_VERSION = 4.3.1104
MLNX_SDK_ISSU_VERSION = 100

MLNX_SDK_DEB_VERSION = $(subst _,.,$(MLNX_SDK_VERSION))

# Place here URL where SDK sources exist
MLNX_SDK_SOURCE_BASE_URL = 

export MLNX_SDK_SOURCE_BASE_URL MLNX_SDK_VERSION MLNX_SDK_ISSU_VERSION MLNX_SDK_DEB_VERSION

MLNX_SDK_RDEBS += $(APPLIBS) $(IPROUTE2_MLNX) $(SX_ACL_RM) $(SX_COMPLIB) \
		  $(SX_EXAMPLES) $(SX_GEN_UTILS) $(SX_SCEW) $(SXD_LIBS)

MLNX_SDK_DEBS += $(APPLIBS_DEV) $(IPROUTE2_MLNX_DEV) $(SX_ACL_RM_DEV) \
		 $(SX_COMPLIB_DEV) $(SX_COMPLIB_DEV_STATIC) $(SX_EXAMPLES_DEV) \
		 $(SX_GEN_UTILS_DEV) $(SX_SCEW_DEV) $(SX_SCEW_DEV_STATIC) \
		 $(SXD_LIBS_DEV) $(SXD_LIBS_DEV_STATIC)

APPLIBS = applibs_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(APPLIBS)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/applibs
$(APPLIBS)_DEPENDS += $(SX_COMPLIB_DEV) $(SX_GEN_UTILS_DEV) $(SXD_LIBS_DEV) $(LIBNL3_DEV) $(LIBNL_GENL3_DEV)
$(APPLIBS)_RDEPENDS += $(SX_COMPLIB) $(SX_GEN_UTILS) $(SXD_LIBS) $(LIBNL3) $(LIBNL_GENL3)
APPLIBS_DEV = applibs-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(APPLIBS),$(APPLIBS_DEV)))

IPROUTE2_MLNX = iproute2_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(IPROUTE2_MLNX)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/iproute2
IPROUTE2_MLNX_DEV = iproute2-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(IPROUTE2_MLNX),$(IPROUTE2_MLNX_DEV)))

SX_COMPLIB = sx-complib_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(SX_COMPLIB)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/sx-complib
SX_COMPLIB_DEV = sx-complib-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(SX_COMPLIB),$(SX_COMPLIB_DEV)))

SX_EXAMPLES = sx-examples_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(SX_EXAMPLES)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/sx-examples
$(SX_EXAMPLES)_DEPENDS += $(APPLIBS_DEV) $(SX_SCEW_DEV) $(SXD_LIBS_DEV)
$(SX_EXAMPLES)_RDEPENDS += $(APPLIBS) $(SX_SCEW) $(SXD_LIBS)
SX_EXAMPLES_DEV = sx-examples-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(SX_EXAMPLES),$(SX_EXAMPLES_DEV)))

SX_GEN_UTILS = sx-gen-utils_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(SX_GEN_UTILS)_SRC_PATH += $(PLATFORM_PATH)/sdk-src/sx-gen-utils
$(SX_GEN_UTILS)_DEPENDS += $(SX_COMPLIB_DEV) $(SXD_LIBS_DEV)
$(SX_GEN_UTILS)_RDEPENDS += $(SX_COMPLIB)
SX_GEN_UTILS_DEV = sx-gen-utils-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(SX_GEN_UTILS),$(SX_GEN_UTILS_DEV)))

SX_SCEW = sx-scew_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(SX_SCEW)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/sx-scew
SX_SCEW_DEV = sx-scew-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(SX_SCEW),$(SX_SCEW_DEV)))

SXD_LIBS = sxd-libs_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(SXD_LIBS)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/sxd-libs
$(SXD_LIBS)_DEPENDS += $(SX_COMPLIB_DEV)
SXD_LIBS_DEV = sxd-libs-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(SXD_LIBS),$(SXD_LIBS_DEV)))

#packages that are required for runtime only
PYTHON_SDK_API = python-sdk-api_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(PYTHON_SDK_API)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/python-sdk-api
$(PYTHON_SDK_API)_DEPENDS += $(APPLIBS_DEV) $(SXD_LIBS_DEV)
$(PYTHON_SDK_API)_RDEPENDS += $(APPLIBS) $(SXD_LIBS)

SX_KERNEL = sx-kernel_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(SX_KERNEL)_DEPENDS += $(LINUX_HEADERS) $(LINUX_HEADERS_COMMON)
$(SX_KERNEL)_SRC_PATH = $(PLATFORM_PATH)/sdk-src/sx-kernel
SX_KERNEL_DEV = sx-kernel-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(SX_KERNEL),$(SX_KERNEL_DEV)))

define make_url
	$(1)_URL = $(MLNX_SDK_BASE_URL)/$(1)

endef

$(eval $(foreach deb,$(MLNX_SDK_DEBS),$(call make_url,$(deb))))
$(eval $(foreach deb,$(MLNX_SDK_RDEBS),$(call make_url,$(deb))))
$(eval $(foreach deb,$(PYTHON_SDK_API) $(SX_KERNEL) $(SX_KERNEL_DEV),$(call make_url,$(deb))))

ifneq ($(MLNX_SDK_SOURCE_BASE_URL), )
SONIC_MAKE_DEBS += $(MLNX_SDK_RDEBS) $(PYTHON_SDK_API) $(SX_KERNEL)
else
SONIC_ONLINE_DEBS += $(MLNX_SDK_RDEBS) $(PYTHON_SDK_API) $(SX_KERNEL)
endif

SONIC_STRETCH_DEBS += $(SX_KERNEL)

mlnx-sdk-packages: $(addprefix $(DEBS_PATH)/, $(MLNX_SDK_RDEBS) $(PYTHON_SDK_API) $(SX_KERNEL))

SONIC_PHONY_TARGETS += mlnx-sdk-packages
