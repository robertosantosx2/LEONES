#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

extern int64_t asmbin_validate(const void *base, uint64_t actual_size);

int main(int argc, char **argv)
{
    int fd;
    struct stat st;
    void *mapping;
    uint64_t file_size;
    int64_t result;
    uint32_t version;

    if (argc != 2) {
        fprintf(stderr, "usage: %s MODEL.asmbin\n", argv[0]);
        return 2;
    }

    fd = open(argv[1], O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        perror("open");
        return 2;
    }

    if (fstat(fd, &st) < 0) {
        perror("fstat");
        close(fd);
        return 2;
    }
    if (!S_ISREG(st.st_mode) || st.st_size <= 0 ||
        (uintmax_t)st.st_size > (uintmax_t)SIZE_MAX) {
        fprintf(stderr, "error: input must be a non-empty regular file representable by size_t\n");
        close(fd);
        return 2;
    }

    file_size = (uint64_t)st.st_size;
    mapping = mmap(NULL, (size_t)file_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (mapping == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 2;
    }
    if (close(fd) < 0) {
        perror("close");
        munmap(mapping, (size_t)file_size);
        return 2;
    }

    result = asmbin_validate(mapping, file_size);
    if (result == 0) {
        memcpy(&version, (const unsigned char *)mapping + 4, sizeof(version));
        printf("ASMBIN_VALID version=%" PRIu32 " bytes=%" PRIu64 "\n",
               version, file_size);
    } else {
        fprintf(stderr, "ASMBIN_INVALID code=%" PRId64 " bytes=%" PRIu64 "\n",
                result, file_size);
    }

    if (munmap(mapping, (size_t)file_size) < 0) {
        perror("munmap");
        return 2;
    }
    return result == 0 ? 0 : 1;
}
