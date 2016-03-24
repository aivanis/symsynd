import os

from symsynd.mach import get_cpu_name, get_macho_uuids


def find_debug_images(dsym_paths, binary_images):
    images_to_load = set()

    for image in binary_images:
        cpu_name = get_cpu_name(image['cpu_type'],
                                image['cpu_subtype'])
        if cpu_name is not None:
            images_to_load.add(image['uuid'].lower())

    images = {}

    # Step one: load images that are named by their UUID
    for uuid in list(images_to_load):
        for dsym_path in dsym_paths:
            fn = os.path.join(dsym_path, uuid)
            if os.path.isfile(fn):
                images[uuid] = fn
                images_to_load.discard(uuid)
                break

    # Otherwise fall back to loading images from the dsym bundle.
    if images_to_load:
        for dsym_path in dsym_paths:
            dwarf_base = os.path.join(dsym_path, 'Contents',
                                      'Resources', 'DWARF')
            if os.path.isdir(dwarf_base):
                for fn in os.listdir(dwarf_base):
                    # Looks like a UUID we loaded, skip it
                    if fn in images:
                        continue
                    full_fn = os.path.join(dwarf_base, fn)
                    uuids = get_macho_uuids(full_fn)
                    for _, uuid in uuids:
                        if uuid in images_to_load:
                            images[uuid] = full_fn
                            images_to_load.discard(uuid)

    rv = {}

    # Now resolve all the images.
    for image in binary_images:
        cpu_name = get_cpu_name(image['cpu_type'],
                                image['cpu_subtype'])
        if cpu_name is None:
            continue
        uid = image['uuid'].lower()
        if uid not in images:
            continue
        rv[image['image_addr']] = {
            'uuid': uid,
            'image_addr': image['image_addr'],
            'dsym_path': images[uid],
            'image_vmaddr': image['image_vmaddr'],
            'cpu_name': cpu_name,
        }

    return rv


class ReportSymbolizer(object):

    def __init__(self, driver, dsym_paths, binary_images):
        if isinstance(dsym_paths, basestring):
            dsym_paths = [dsym_paths]
        self.driver = driver
        self.images = find_debug_images(dsym_paths, binary_images)

    def symbolize_backtrace(self, backtrace):
        rv = []
        for frame in backtrace:
            frame = dict(frame)
            img = self.images.get(frame['object_addr'])
            if img is not None:
                frame.update(self.driver.symbolize(
                    img['dsym_path'], img['image_vmaddr'],
                    img['image_addr'], frame['instruction_addr'],
                    img['cpu_name'], img['uuid']))
            rv.append(frame)
        return rv
