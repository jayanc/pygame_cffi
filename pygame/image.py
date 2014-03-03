""" The pygame image module """

from pygame._error import SDLError
from pygame._sdl import sdl, ffi, get_sdl_byteorder
from pygame.imageext import load_extended, save_extended
from pygame.surface import Surface, locked, BYTE0, BYTE1, BYTE2


def get_extended():
    # Only correct if we always require SDL_image
    return True


def load_basic(filename, namehint=""):
    # Will we need this, if we're always requiring SDL_image?
    raise NotImplementedError()


# Pygame allows load, load_basic and load_extended to be
# imported while only a single save function is exposed.
# Not sure if it is intentional but keeping it that way.
if get_extended():
    load = load_basic

    def save(surf, filename):
        """ save(Surface, filename) -> None
        save an image to disk
        """
        raise NotImplementedError()
else:
    load = load_extended
    save = save_extended


def fromstring(string, (w, h), format, flipped=False):
    if w < 1 or h < 1:
        raise ValueError("Resolution must be positive values")

    if format == "P":
        if len(string) != w * h:
            raise ValueError("String length does not equal format and "
                             "resolution size")
        surf = sdl.SDL_CreateRGBSurface(0, w, h, 8, 0, 0, 0, 0)
        if not surf:
            raise SDLError.from_sdl_error()
        with locked(surf):
            pixels = ffi.cast('char*', surf.pixels)
            for y in range(h):
                dest =  surf.pitch * y
                src_start = (h - 1 - y) * w if flipped else y * w
                pixels[dest:dest + w] = string[src_start:src_start + w]

    elif format == "RGB":
        if len(string) != w * h * 3:
            raise ValueError("String length does not equal format and "
                             "resolution size")
        surf = sdl.SDL_CreateRGBSurface(0, w, h, 24, 0xff, 0xff << 16,
                                        0xff << 8, 0)
        if not surf:
            raise SDLError.from_sdl_error()
        with locked(surf):
            pixels = ffi.cast("char*", surf.pixels)
            for y in range(h):
                dest = surf.pitch * y
                src_start = (h - 1 - y) * w * 3 if flipped else y * w * 3
                row = string[src_start:src_start + w * 3]
                for x in range(0, w * 3, 3):
                    # BYTE0, BYTE1 and BYTE2 are determined by byte order
                    pixels[dest + x + BYTE0] = row[x + BYTE0]
                    pixels[dest + x + BYTE1] = row[x + BYTE1]
                    pixels[dest + x + BYTE2] = row[x + BYTE2]

    elif format in ("RGBA", "RGBAX", "ARGB"):
        if len(string) != w * h * 4:
            raise ValueError("String length does not equal format and "
                             "resolution size")
        if format == "ARGB":
            if get_sdl_byteorder() == sdl.SDL_LIL_ENDIAN:
                rmask, gmask, bmask, amask = (0xff << 8, 0xff << 16,
                                              0xff << 24, 0xff)
            else:
                rmask, gmask, bmask, amask = (0xff << 16, 0xff << 8,
                                              0xff, 0xff << 24)
            surf = sdl.SDL_CreateRGBSurface(sdl.SDL_SRCALPHA, w, h, 32,
                                            rmask, gmask, bmask, amask)
        else:
            alphamult = format == "RGBA"
            if get_sdl_byteorder() == sdl.SDL_LIL_ENDIAN:
                rmask, gmask, bmask = 0xff, 0xff << 8, 0xff << 16
                amask = 0xff << 24 if alphamult else 0
            else:
                rmask, gmask, bmask = 0xff << 24, 0xff << 16, 0xff << 8
                amask = 0xff if alphamult else 0
            surf = sdl.SDL_CreateRGBSurface(sdl.SDL_SRCALPHA if alphamult
                                            else 0, w, h, 32, rmask, gmask,
                                            bmask, amask)
        if not surf:
            raise SDLError.from_sdl_error()
        with locked(surf):
            pixels = ffi.cast("char*", surf.pixels)
            for y in range(h):
                dest = surf.pitch * y
                src_start = (h - 1 - y) * w * 4 if flipped else y * w * 4
                pixels[dest:dest + w * 4]  = string[src_start:src_start + w * 4]

    else:
        raise ValueError("Unrecognized type of format")

    return Surface._from_sdl_surface(surf)


def tostring(surface, format, flipped=False):
    """ tostring(Surface, format, flipped=False) -> string
    transfer image to string buffer
    """
    surf = surface._c_surface
    if surf.flags & sdl.SDL_OPENGL:
        raise NotImplementedError()

    if format == "P":
        if surf.format.BytesPerPixel != 1:
            raise ValueError("Can only create \"P\" format data with "
                             "8bit Surfaces")
        with locked(surf):
            string = ffi.buffer(ffi.cast('char*', surf.pixels))[:]
    elif format in ("RGBA_PREMULT", "ARGB_PREMULT", "ARGB"):
        raise NotImplementedError()
    else:
        _tostring = globals().get('_tostring_%s' % format, None)
        if _tostring is None:
            raise ValueError("Unrecognized type of format")
        with locked(surf):
            string = _tostring(surf, flipped)
    return string


def _tostring_RGBA(surf, flipped, has_colorkey=True):
    rmask, gmask, bmask, amask = (surf.format.Rmask,
                                  surf.format.Gmask,
                                  surf.format.Bmask,
                                  surf.format.Amask)
    rshift, gshift, bshift, ashift = (surf.format.Rshift,
                                      surf.format.Gshift,
                                      surf.format.Bshift,
                                      surf.format.Ashift)
    rloss, gloss, bloss, aloss = (surf.format.Rloss,
                                  surf.format.Gloss,
                                  surf.format.Bloss,
                                  surf.format.Aloss)
    bpp = surf.format.BytesPerPixel
    h, w = surf.h, surf.w
    has_colorkey = (has_colorkey and surf.flags & sdl.SDL_SRCCOLORKEY
                    and not amask)
    colorkey = surf.format.colorkey

    data = ffi.new('char[]', w * h * 4)
    if bpp == 1:
        pixels = ffi.cast('uint8_t*', surf.pixels)
        colors = surf.format.palette.colors
        for y in range(h):
            src_start = (h - 1 - y) * w if flipped \
                        else y * w
            for x in range(w):
                dest = 4 * (y * w + x)
                color = pixels[src_start + x]
                data[dest] = chr(colors[color].r)
                data[dest + 1] = chr(colors[color].g)
                data[dest + 2] = chr(colors[color].b)
                if has_colorkey:
                    data[dest + 3] = chr(ffi.cast('char', color != colorkey) * 255)
                else:
                    data[dest + 3] = chr(255)
    elif bpp == 2:
        pixels = ffi.cast('uint16_t*', surf.pixels)
        for y in range(h):
            src_start = (h - 1 - y) * w if flipped \
                        else y * w
            for x in range(w):
                dest = 4 * (y * w + x)
                color = pixels[src_start + x]
                data[dest] = chr(((color & rmask) >> rshift) << rloss)
                data[dest + 1] = chr(((color & gmask) >> gshift) << gloss)
                data[dest + 2] = chr(((color & bmask) >> bshift) << bloss)
                if has_colorkey:
                    data[dest + 3] = chr(ffi.cast('char', color != colorkey) * 255)
                else:
                    data[dest + 3] = chr((((color & amask) >> ashift) << aloss)
                                         if amask else 255)
    elif bpp == 3:
        pixels = ffi.cast('uint8_t*', surf.pixels)
        for y in range(h):
            src_start = (h - 1 - y) * surf.pitch if flipped \
                        else y * surf.pitch
            for x in range(w):
                dest = 4 * (y * w + x)
                color = (pixels[src_start + x * 4 + BYTE0] +
                         (pixels[src_start + x * 4 + BYTE1] << 8) +
                         (pixels[src_start + x * 4 + BYTE2] << 16))
                data[dest] = chr(((color & rmask) >> rshift) << rloss)
                data[dest + 1] = chr(((color & gmask) >> gshift) << gloss)
                data[dest + 2] = chr(((color & bmask) >> bshift) << bloss)
                if has_colorkey:
                    data[dest + 3] = chr(ffi.cast('char', color != colorkey) * 255)
                else:
                    data[dest + 3] = chr((((color & amask) >> ashift) << aloss)
                                         if amask else 255)
    elif bpp == 4:
        pixels = ffi.cast('uint32_t*', surf.pixels)
        for y in range(h):
            src_start = (h - 1 - y) * w if flipped \
                        else y * w
            for x in range(w):
                dest = 4 * (y * w + x)
                color = pixels[src_start + x]
                data[dest] = chr(((color & rmask) >> rshift) << rloss)
                data[dest + 1] = chr(((color & gmask) >> gshift) << gloss)
                data[dest + 2] = chr(((color & bmask) >> bshift) << bloss)
                if has_colorkey:
                    data[dest + 3] = chr(ffi.cast('char', color != colorkey) * 255)
                else:
                    data[dest + 3] = chr((((color & amask) >> ashift) << aloss)
                                         if amask else 255)
    else:
        raise ValueError("invalid color depth")
    return ffi.buffer(data)[:]


def _tostring_RGBX(surf, flipped):
    return _tostring_RGBA(surf, flipped, False)


def _tostring_RGB(surf, flipped):
    rmask, gmask, bmask, amask = (surf.format.Rmask,
                                  surf.format.Gmask,
                                  surf.format.Bmask,
                                  surf.format.Amask)
    rshift, gshift, bshift, ashift = (surf.format.Rshift,
                                      surf.format.Gshift,
                                      surf.format.Bshift,
                                      surf.format.Ashift)
    rloss, gloss, bloss, aloss = (surf.format.Rloss,
                                  surf.format.Gloss,
                                  surf.format.Bloss,
                                  surf.format.Aloss)
    bpp = surf.format.BytesPerPixel
    h, w = surf.h, surf.w

    data = ffi.new('char[]', w * h * 3)
    if bpp == 1:
        pixels = ffi.cast('uint8_t*', surf.pixels)
        colors = surf.format.palette.colors
        for y in range(h):
            src_start = (h - 1 - y) * w if flipped \
                        else y * w
            for x in range(w):
                dest = 3 * (y * w + x)
                color = pixels[src_start + x]
                data[dest] = chr(colors[color].r)
                data[dest + 1] = chr(colors[color].g)
                data[dest + 2] = chr(colors[color].b)
    elif bpp == 2:
        pixels = ffi.cast('uint16_t*', surf.pixels)
        for y in range(h):
            src_start = (h - 1 - y) * w if flipped \
                        else y * w
            for x in range(w):
                dest = 3 * (y * w + x)
                color = pixels[src_start + x]
                data[dest] = chr(((color & rmask) >> rshift) << rloss)
                data[dest + 1] = chr(((color & gmask) >> gshift) << gloss)
                data[dest + 2] = chr(((color & bmask) >> bshift) << bloss)
    elif bpp == 3:
        pixels = ffi.cast('uint8_t*', surf.pixels)
        for y in range(h):
            src_start = (h - 1 - y) * surf.pitch if flipped \
                        else y * surf.pitch
            for x in range(w):
                dest = 3 * (y * w + x)
                color = (pixels[src_start + x * 3 + BYTE0] +
                         (pixels[src_start + x * 3 + BYTE1] << 8) +
                         (pixels[src_start + x * 3 + BYTE2] << 16))
                data[dest] = chr(((color & rmask) >> rshift) << rloss)
                data[dest + 1] = chr(((color & gmask) >> gshift) << gloss)
                data[dest + 2] = chr(((color & bmask) >> bshift) << bloss)
    elif bpp == 4:
        pixels = ffi.cast('uint32_t*', surf.pixels)
        for y in range(h):
            src_start = (h - 1 - y) * w if flipped \
                        else y * w
            for x in range(w):
                dest = 3 * (y * w + x)
                color = pixels[src_start + x]
                data[dest] = chr(((color & rmask) >> rshift) << rloss)
                data[dest + 1] = chr(((color & gmask) >> gshift) << gloss)
                data[dest + 2] = chr(((color & bmask) >> bshift) << bloss)
    else:
        raise ValueError("invalid color depth")
    return ffi.buffer(data)[:]


def frombuffer(string, size, format):
    """ frombuffer(string, size, format) -> Surface
    create a new Surface that shares data inside a string buffer
    """
    raise NotImplementedError()
