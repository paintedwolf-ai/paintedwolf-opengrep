#import <Foundation/Foundation.h>
#import <Security/Security.h>
#import <CommonCrypto/CommonDigest.h>
#import <mach-o/arch.h>
#import <mach-o/fat.h>
#import <mach-o/loader.h>
#import <libkern/OSByteOrder.h>
#import <sys/stat.h>
#import <fcntl.h>
#import <unistd.h>

static void emit(NSDictionary *value, int status) {
    NSData *data = [NSJSONSerialization dataWithJSONObject:value options:NSJSONWritingSortedKeys error:nil];
    if (!data || data.length > 1024 * 1024) exit(2);
    fwrite(data.bytes, 1, data.length, stdout);
    fputc('\n', stdout);
    exit(status);
}

static void fail(NSString *stage, NSString *code, OSStatus status) {
    emit(@{@"schema_version": @1, @"ok": @NO,
           @"error": @{@"stage": stage, @"code": code, @"osstatus": @(status)}}, 1);
}

static NSString *hexDigest(const unsigned char *bytes) {
    NSMutableString *value = [NSMutableString stringWithCapacity:64];
    for (unsigned i = 0; i < CC_SHA256_DIGEST_LENGTH; i++) [value appendFormat:@"%02x", bytes[i]];
    return value;
}

static NSString *fileDigest(int fd, off_t size) {
    CC_SHA256_CTX context;
    CC_SHA256_Init(&context);
    unsigned char buffer[1024 * 1024];
    off_t offset = 0;
    while (offset < size) {
        ssize_t count = pread(fd, buffer, (size_t)MIN((off_t)sizeof(buffer), size - offset), offset);
        if (count <= 0) fail(@"image", @"read_failed", 0);
        CC_SHA256_Update(&context, buffer, (CC_LONG)count);
        offset += count;
    }
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256_Final(digest, &context);
    return hexDigest(digest);
}

static void readExact(int fd, void *buffer, size_t bytes, off_t offset) {
    if (pread(fd, buffer, bytes, offset) != (ssize_t)bytes) fail(@"architecture", @"truncated_header", 0);
}

static NSDictionary *thinSlice(int fd, uint64_t offset, uint64_t size, uint64_t total) {
    if (offset > total || size > total - offset || size < sizeof(struct mach_header))
        fail(@"architecture", @"invalid_slice_bounds", 0);
    struct mach_header header;
    readExact(fd, &header, sizeof(header), (off_t)offset);
    bool swapped = header.magic == MH_CIGAM || header.magic == MH_CIGAM_64;
    if (!swapped && header.magic != MH_MAGIC && header.magic != MH_MAGIC_64)
        fail(@"architecture", @"not_macho", 0);
    uint32_t cpu = swapped ? OSSwapInt32(header.cputype) : (uint32_t)header.cputype;
    uint32_t subtype = swapped ? OSSwapInt32(header.cpusubtype) : (uint32_t)header.cpusubtype;
    const NXArchInfo *arch = NXGetArchInfoFromCpuType((cpu_type_t)cpu, (cpu_subtype_t)subtype);
    if (!arch) fail(@"architecture", @"unsupported_cpu", 0);
    return @{@"architecture": @(arch->name), @"cpu_type": @(cpu), @"cpu_subtype": @(subtype),
             @"offset": @(offset), @"size": @(size)};
}

static NSArray *imageSlices(int fd, uint64_t total) {
    uint32_t magic;
    readExact(fd, &magic, sizeof(magic), 0);
    bool fat32 = magic == FAT_MAGIC || magic == FAT_CIGAM;
    bool fat64 = magic == FAT_MAGIC_64 || magic == FAT_CIGAM_64;
    if (!fat32 && !fat64) return @[thinSlice(fd, 0, total, total)];
    bool swapped = magic == FAT_CIGAM || magic == FAT_CIGAM_64;
    uint32_t count;
    readExact(fd, &count, sizeof(count), 4);
    if (swapped) count = OSSwapInt32(count);
    if (!count || count > 32) fail(@"architecture", @"invalid_slice_count", 0);
    NSMutableArray *slices = [NSMutableArray array];
    uint64_t tableEnd = 8 + count * (fat64 ? sizeof(struct fat_arch_64) : sizeof(struct fat_arch));
    for (uint32_t i = 0; i < count; i++) {
        uint64_t offset, size;
        uint32_t cpu, subtype;
        if (fat64) {
            struct fat_arch_64 entry;
            readExact(fd, &entry, sizeof(entry), 8 + i * sizeof(entry));
            offset = swapped ? OSSwapInt64(entry.offset) : entry.offset;
            size = swapped ? OSSwapInt64(entry.size) : entry.size;
            cpu = swapped ? OSSwapInt32(entry.cputype) : (uint32_t)entry.cputype;
            subtype = swapped ? OSSwapInt32(entry.cpusubtype) : (uint32_t)entry.cpusubtype;
        } else {
            struct fat_arch entry;
            readExact(fd, &entry, sizeof(entry), 8 + i * sizeof(entry));
            offset = swapped ? OSSwapInt32(entry.offset) : entry.offset;
            size = swapped ? OSSwapInt32(entry.size) : entry.size;
            cpu = swapped ? OSSwapInt32(entry.cputype) : (uint32_t)entry.cputype;
            subtype = swapped ? OSSwapInt32(entry.cpusubtype) : (uint32_t)entry.cpusubtype;
        }
        NSDictionary *slice = thinSlice(fd, offset, size, total);
        if (offset < tableEnd || [slice[@"cpu_type"] unsignedIntValue] != cpu || [slice[@"cpu_subtype"] unsignedIntValue] != subtype)
            fail(@"architecture", @"inconsistent_slice", 0);
        for (NSDictionary *prior in slices) {
            uint64_t start = [prior[@"offset"] unsignedLongLongValue];
            uint64_t end = start + [prior[@"size"] unsignedLongLongValue];
            if ((offset < end && start < offset + size) ||
                ([prior[@"cpu_type"] isEqual:slice[@"cpu_type"]] && [prior[@"cpu_subtype"] isEqual:slice[@"cpu_subtype"]]))
                fail(@"architecture", @"overlapping_or_duplicate_slice", 0);
        }
        [slices addObject:slice];
    }
    return slices;
}

static BOOL matches(NSString *value, NSString *pattern) {
    NSRange range = [value rangeOfString:pattern options:NSRegularExpressionSearch];
    return range.location == 0 && range.length == value.length;
}

static void certificateProfile(NSString *filename) {
    struct stat info;
    if (lstat(filename.fileSystemRepresentation, &info) || !S_ISREG(info.st_mode) || info.st_size <= 0 || info.st_size > 1024 * 1024)
        fail(@"certificate", @"invalid_file", 0);
    NSData *der = [NSData dataWithContentsOfFile:filename];
    if (!der || der.length != (NSUInteger)info.st_size) fail(@"certificate", @"read_failed", 0);
    SecCertificateRef certificate = SecCertificateCreateWithData(NULL, (__bridge CFDataRef)der);
    if (!certificate) fail(@"certificate", @"invalid_der", 0);
    NSArray *keys = @[(__bridge NSString *)kSecOIDX509V1SubjectName];
    CFErrorRef error = NULL;
    CFDictionaryRef values = SecCertificateCopyValues(certificate, (__bridge CFArrayRef)keys, &error);
    CFRelease(certificate);
    if (error) CFRelease(error);
    if (!values) fail(@"certificate", @"subject_values_missing", 0);
    NSDictionary *properties = CFBridgingRelease(values);
    id property = properties[(__bridge NSString *)kSecOIDX509V1SubjectName];
    id subject = [property isKindOfClass:NSDictionary.class] ? property[(__bridge NSString *)kSecPropertyKeyValue] : nil;
    if (![subject isKindOfClass:NSArray.class]) fail(@"certificate", @"subject_values_missing", 0);
    id team = nil;
    for (id attribute in subject) {
        if (![attribute isKindOfClass:NSDictionary.class]) fail(@"certificate", @"invalid_subject_attribute", 0);
        if (![attribute[(__bridge NSString *)kSecPropertyKeyLabel] isEqual:(__bridge NSString *)kSecOIDOrganizationalUnitName]) continue;
        if (team) fail(@"certificate", @"single_team_ou_required", 0);
        team = attribute[(__bridge NSString *)kSecPropertyKeyValue];
    }
    if (![team isKindOfClass:NSString.class] || !matches(team, @"^[A-Z0-9]{10}$"))
        fail(@"certificate", @"single_team_ou_required", 0);
    unsigned char bytes[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256(der.bytes, (CC_LONG)der.length, bytes);
    emit(@{@"schema_version": @1, @"mode": @"developer-id", @"team_id": team, @"certificate_sha256": hexDigest(bytes)}, 0);
}

static NSDictionary *inspectSlice(NSURL *url, NSDictionary *slice, NSString *mode, NSString *team, NSString *fingerprint) {
    NSDictionary *attributes = @{(__bridge NSString *)kSecCodeAttributeArchitecture: @((cpu_type_t)[slice[@"cpu_type"] unsignedIntValue]),
                                 (__bridge NSString *)kSecCodeAttributeSubarchitecture: @((cpu_subtype_t)[slice[@"cpu_subtype"] unsignedIntValue]),
                                 (__bridge NSString *)kSecCodeAttributeUniversalFileOffset: slice[@"offset"]};
    SecStaticCodeRef code = NULL;
    OSStatus status = SecStaticCodeCreateWithPathAndAttributes((__bridge CFURLRef)url, kSecCSDefaultFlags,
                                                              (__bridge CFDictionaryRef)attributes, &code);
    if (status) fail(@"create", @"security_status", status);
    SecRequirementRef requirement = NULL;
    if ([mode isEqual:@"developer-id"]) {
        NSString *text = [NSString stringWithFormat:@"anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] exists and certificate leaf[field.1.2.840.113635.100.6.1.13] exists and certificate leaf[subject.OU] = \"%@\"", team];
        status = SecRequirementCreateWithString((__bridge CFStringRef)text, kSecCSDefaultFlags, &requirement);
        if (status) fail(@"requirement", @"security_status", status);
    }
    status = SecStaticCodeCheckValidity(code, kSecCSStrictValidate | kSecCSSingleThreaded, requirement);
    if (requirement) CFRelease(requirement);
    if (status) fail(@"validity", @"security_status", status);
    CFDictionaryRef information = NULL;
    // Security.framework requires validity before signing information becomes authoritative.
    status = SecCodeCopySigningInformation(code, kSecCSSigningInformation, &information);
    CFRelease(code);
    if (status) fail(@"information", @"security_status", status);
    NSDictionary *info = CFBridgingRelease(information);
    id identifier = info[(__bridge NSString *)kSecCodeInfoIdentifier];
    id flags = info[(__bridge NSString *)kSecCodeInfoFlags];
    id actualTeam = info[(__bridge NSString *)kSecCodeInfoTeamIdentifier];
    id timestamp = info[(__bridge NSString *)kSecCodeInfoTimestamp];
    id entitlements = info[(__bridge NSString *)kSecCodeInfoEntitlementsDict];
    id certificates = info[(__bridge NSString *)kSecCodeInfoCertificates];
    if (![identifier isKindOfClass:NSString.class] || ![identifier length] || [identifier length] > 4096 ||
        !flags || CFGetTypeID((__bridge CFTypeRef)flags) != CFNumberGetTypeID())
        fail(@"information", @"missing_identity_or_flags", 0);
    if (entitlements && (![entitlements isKindOfClass:NSDictionary.class] || [entitlements count] != 0))
        fail(@"policy", @"unexpected_entitlements", 0);
    if (!entitlements && info[(__bridge NSString *)kSecCodeInfoEntitlements])
        fail(@"information", @"unparsed_entitlements", 0);
    if (actualTeam && ![actualTeam isKindOfClass:NSString.class]) fail(@"information", @"malformed_team", 0);
    if (timestamp && CFGetTypeID((__bridge CFTypeRef)timestamp) != CFDateGetTypeID()) fail(@"information", @"malformed_timestamp", 0);
    NSString *leaf = nil;
    if (certificates) {
        if (![certificates isKindOfClass:NSArray.class]) fail(@"information", @"malformed_certificates", 0);
        if ([certificates count]) {
            CFTypeRef certificate = (__bridge CFTypeRef)certificates[0];
            if (CFGetTypeID(certificate) != SecCertificateGetTypeID()) fail(@"information", @"malformed_certificate", 0);
            NSData *der = CFBridgingRelease(SecCertificateCopyData((SecCertificateRef)certificate));
            if (!der.length || der.length > 1024 * 1024) fail(@"information", @"malformed_certificate", 0);
            unsigned char bytes[CC_SHA256_DIGEST_LENGTH];
            CC_SHA256(der.bytes, (CC_LONG)der.length, bytes);
            leaf = hexDigest(bytes);
        }
    }
    uint32_t bits = [flags unsignedIntValue];
    if ([mode isEqual:@"developer-id"]) {
        if ((bits & kSecCodeSignatureAdhoc) || !(bits & kSecCodeSignatureRuntime)) fail(@"policy", @"runtime_or_identity_missing", 0);
        if (![actualTeam isEqual:team] || ![leaf isEqual:fingerprint]) fail(@"policy", @"signer_mismatch", 0);
        if (!timestamp) fail(@"policy", @"secure_timestamp_missing", 0);
    } else if (!(bits & kSecCodeSignatureAdhoc) || actualTeam || leaf || timestamp) {
        fail(@"policy", @"not_adhoc", 0);
    }
    NSISO8601DateFormatter *formatter = [NSISO8601DateFormatter new];
    NSMutableDictionary *result = [slice mutableCopy];
    [result removeObjectsForKeys:@[@"offset", @"size"]];
    [result addEntriesFromDictionary:@{@"identifier": identifier, @"flags": @(bits), @"team_id": actualTeam ?: NSNull.null,
                                       @"certificate_sha256": leaf ?: NSNull.null,
                                       @"secure_timestamp": timestamp ? [formatter stringFromDate:timestamp] : NSNull.null,
                                       @"entitlements": entitlements ?: @{}}];
    return result;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc == 3 && strcmp(argv[1], "--certificate") == 0) certificateProfile(@(argv[2]));
        if (argc != 5) fail(@"arguments", @"invalid_arguments", 0);
        NSString *filename = @(argv[1]), *mode = @(argv[2]), *team = @(argv[3]), *fingerprint = @(argv[4]);
        BOOL developer = [mode isEqual:@"developer-id"];
        if ((developer && (!matches(team, @"^[A-Z0-9]{10}$") || !matches(fingerprint, @"^[a-f0-9]{64}$"))) ||
            (!developer && (![mode isEqual:@"adhoc"] || team.length || fingerprint.length))) fail(@"arguments", @"invalid_profile", 0);
        int fd = open(argv[1], O_RDONLY | O_NOFOLLOW);
        struct stat before, after;
        if (fd < 0 || fstat(fd, &before) || !S_ISREG(before.st_mode) || before.st_size < 4 || before.st_size > (off_t)8 * 1024 * 1024 * 1024)
            fail(@"image", @"invalid_file", 0);
        NSString *digest = fileDigest(fd, before.st_size);
        NSMutableArray *records = [NSMutableArray array];
        NSURL *url = [NSURL fileURLWithPath:filename.stringByStandardizingPath];
        for (NSDictionary *slice in imageSlices(fd, (uint64_t)before.st_size))
            [records addObject:inspectSlice(url, slice, mode, team, fingerprint)];
        if (fstat(fd, &after) || before.st_size != after.st_size || ![digest isEqual:fileDigest(fd, after.st_size)])
            fail(@"image", @"changed_during_inspection", 0);
        struct stat current;
        if (lstat(argv[1], &current) || current.st_dev != before.st_dev || current.st_ino != before.st_ino)
            fail(@"image", @"replaced_during_inspection", 0);
        close(fd);
        emit(@{@"schema_version": @1, @"ok": @YES, @"sha256": digest, @"bytes": @(before.st_size), @"slices": records}, 0);
    }
}
