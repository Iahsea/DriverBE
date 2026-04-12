#include <linux/module.h>
#include <linux/export-internal.h>
#include <linux/compiler.h>

MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};



static const struct modversion_info ____versions[]
__used __section("__versions") = {
	{ 0xa1dacb42, "class_destroy" },
	{ 0x4e54d6ac, "cdev_del" },
	{ 0x0bc5fb0d, "unregister_chrdev_region" },
	{ 0xbd03ed67, "__ref_stack_chk_guard" },
	{ 0x90a48d82, "__ubsan_handle_out_of_bounds" },
	{ 0xd272d446, "__stack_chk_fail" },
	{ 0x82fd7238, "__ubsan_handle_shift_out_of_bounds" },
	{ 0x1595e410, "device_destroy" },
	{ 0xa53f4e29, "memcpy" },
	{ 0x75738bed, "__warn_printk" },
	{ 0xe4de56b4, "__ubsan_handle_load_invalid_value" },
	{ 0xbd03ed67, "random_kmalloc_seed" },
	{ 0xfaabfe5e, "kmalloc_caches" },
	{ 0xc064623f, "__kmalloc_cache_noprof" },
	{ 0x092a35a2, "_copy_from_user" },
	{ 0x092a35a2, "_copy_to_user" },
	{ 0xcb8b6ec6, "kfree" },
	{ 0xd272d446, "__fentry__" },
	{ 0xd272d446, "__x86_return_thunk" },
	{ 0x9f222e1e, "alloc_chrdev_region" },
	{ 0xd5f66efd, "cdev_init" },
	{ 0x8ea73856, "cdev_add" },
	{ 0x653aa194, "class_create" },
	{ 0xe486c4b7, "device_create" },
	{ 0xe8213e80, "_printk" },
	{ 0xbebe66ff, "module_layout" },
};

static const u32 ____version_ext_crcs[]
__used __section("__version_ext_crcs") = {
	0xa1dacb42,
	0x4e54d6ac,
	0x0bc5fb0d,
	0xbd03ed67,
	0x90a48d82,
	0xd272d446,
	0x82fd7238,
	0x1595e410,
	0xa53f4e29,
	0x75738bed,
	0xe4de56b4,
	0xbd03ed67,
	0xfaabfe5e,
	0xc064623f,
	0x092a35a2,
	0x092a35a2,
	0xcb8b6ec6,
	0xd272d446,
	0xd272d446,
	0x9f222e1e,
	0xd5f66efd,
	0x8ea73856,
	0x653aa194,
	0xe486c4b7,
	0xe8213e80,
	0xbebe66ff,
};
static const char ____version_ext_names[]
__used __section("__version_ext_names") =
	"class_destroy\0"
	"cdev_del\0"
	"unregister_chrdev_region\0"
	"__ref_stack_chk_guard\0"
	"__ubsan_handle_out_of_bounds\0"
	"__stack_chk_fail\0"
	"__ubsan_handle_shift_out_of_bounds\0"
	"device_destroy\0"
	"memcpy\0"
	"__warn_printk\0"
	"__ubsan_handle_load_invalid_value\0"
	"random_kmalloc_seed\0"
	"kmalloc_caches\0"
	"__kmalloc_cache_noprof\0"
	"_copy_from_user\0"
	"_copy_to_user\0"
	"kfree\0"
	"__fentry__\0"
	"__x86_return_thunk\0"
	"alloc_chrdev_region\0"
	"cdev_init\0"
	"cdev_add\0"
	"class_create\0"
	"device_create\0"
	"_printk\0"
	"module_layout\0"
;

MODULE_INFO(depends, "");


MODULE_INFO(srcversion, "0178C560E4E157D2DD71407");
