# BFN Platform modules

WNC_RSEB_W2_32_PLATFORM_MODULE_VERSION = 1.0
WNC_RSEB_W1_32_PLATFORM_MODULE_VERSION = 1.0

export WNC_RSEB_W2_32_PLATFORM_MODULE_VERSION
export WNC_RSEB_W1_32_PLATFORM_MODULE_VERSION

WNC_RSEB_W2_32_PLATFORM_MODULE = platform-modules-rseb-w2-32_$(WNC_RSEB_W2_32_PLATFORM_MODULE_VERSION)_amd64.deb
$(WNC_RSEB_W2_32_PLATFORM_MODULE)_SRC_PATH = $(PLATFORM_PATH)/sonic-platform-modules-wnc
$(WNC_RSEB_W2_32_PLATFORM_MODULE)_DEPENDS += $(LINUX_HEADERS) $(LINUX_HEADERS_COMMON)
$(WNC_RSEB_W2_32_PLATFORM_MODULE)_PLATFORM = x86_64-wnc_rseb_w2_32-r0
SONIC_DPKG_DEBS += $(WNC_RSEB_W2_32_PLATFORM_MODULE)

WNC_RSEB_W1_32_PLATFORM_MODULE = platform-modules-rseb-w1-32_$(WNC_RSEB_W1_32_PLATFORM_MODULE_VERSION)_amd64.deb
$(WNC_RSEB_W1_32_PLATFORM_MODULE)_PLATFORM = x86_64-wnc_rseb_w1_32-r0
$(eval $(call add_extra_package,$(WNC_RSEB_W2_32_PLATFORM_MODULE),$(WNC_RSEB_W1_32_PLATFORM_MODULE)))

SONIC_STRETCH_DEBS += $(WNC_RSEB_W2_32_PLATFORM_MODULE)