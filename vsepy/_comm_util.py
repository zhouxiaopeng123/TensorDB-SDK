# coding=utf-8
import struct as _stu
import sys as _sys
import socket as _sock

if _sys.version[0] == '2':
    from cStringIO import _BytesIO

    def _s2b(sv):
        return sv.encode() if isinstance(sv, unicode) else sv
else:
    from io import BytesIO as _BytesIO

    def _s2b(sv):
        return sv if isinstance(sv, bytes) else sv.encode()


class SeqReader2(object):
    def __init__(self, dat: bytes, off=0):
        assert isinstance(dat, bytes)
        self.__bts = dat
        self.__off = off

    offset = property(lambda self: self.__off,
                      doc='data sequence read offset')

    left_bytes = property(lambda self: len(self.__bts) - self.__off,
                          doc='data sequence left bytes that can be read')

    def __readtype(self, typelen, fmt):
        tmp = self.__bts[self.__off: self.__off + typelen]
        self.__off += typelen
        return _stu.unpack(fmt, tmp)
    
    def left_data(self):
        return self.__bts[self.__off:]

    def read_types(self, fmts):
        sz = _stu.calcsize(fmts)
        tmp = self.__bts[self.__off: self.__off + sz]
        self.__off += sz
        return _stu.unpack(fmts, tmp)

    def read_bytes(self, sz):
        tmp = self.__bts[self.__off: self.__off + sz]
        self.__off += sz
        return tmp

    def rd_bstr(self):
        sz = self.rd_int()
        return self.read_bytes(sz)

    def rd_int(self):
        return self.__readtype(4, '<I')[0]

    def rd_long(self):
        return self.__readtype(8, '<q')[0]

    def rd_float(self):
        return self.__readtype(4, '<f')[0]


def sock_recv_all(sock: _sock.socket, rcvlen: int):
    tmpbuf, off = _BytesIO(), 0
    try:
        while off < rcvlen:
            rbt = sock.recv(min(rcvlen - off, 1024 * 1024))
            if len(rbt) == 0:
                break
            tmpbuf.write(rbt)
            off += len(rbt)
        return tmpbuf.getvalue()
    finally:
        tmpbuf.close()


def sock_conn_server(server_addr: tuple, conn_tmo_ms: float) -> _sock.socket:
    s = None
    try:
        s = _sock.create_connection(server_addr, conn_tmo_ms / 1000.0)
        s.setsockopt(_sock.IPPROTO_TCP, _sock.TCP_NODELAY, 1)
        s.setblocking(True)
        return s
    except:
        if s:
            s.close()
        raise


"""
class PutChsText(object):
    def __init__(self, ttf):
        self._face = _ft.Face(ttf)
        #hscale = 1.0
        #matrix = _ft.Matrix(int(hscale)*0x10000, int(0.2*0x10000), \
        #                    int(0.0*0x10000), int(1.1*0x10000))
        #pen_translate = _ft.Vector()
        #self._face.set_transform(matrix, pen_translate)

    def draw_text(self, image, pos, text, text_size, text_color):
        '''
        draw chinese(or not) text with ttf
        :param image:     image(numpy.ndarray) to draw text
        :param pos:       where to draw text
        :param text:      the context, for chinese should be unicode type
        :param text_size: text size
        :param text_color:text color
        :return:          image
        '''
        self._face.set_char_size(text_size * 64)
        metrics = self._face.size
        ascender = metrics.ascender/64.0

        #descender = metrics.descender/64.0
        #height = metrics.height/64.0
        #linegap = height - ascender + descender
        ypos = int(ascender)

        if not isinstance(text, str):
            text = text.decode('utf-8')
        img = self.draw_string(image, pos[0], pos[1]+ypos, text, text_color)
        return img

    def draw_string(self, img, x_pos, y_pos, text, color):
        '''
        draw string
        :param x_pos: text x-postion on img
        :param y_pos: text y-postion on img
        :param text:  text (unicode)
        :param color: text color
        :return:      image
        '''
        prev_char = 0
        px = x_pos << 6   # div 64
        py = y_pos << 6

        cur_pen = _ft.Vector()

        for cur_char in text:
            self._face.load_char(cur_char)
            kerning = self._face.get_kerning(prev_char, cur_char)
            px += kerning.x
            slot = self._face.glyph

            cur_pen.x = px
            cur_pen.y = py - slot.bitmap_top * 64
            self.draw_ft_bitmap(img, slot.bitmap, cur_pen, color)

            px += slot.advance.x
            prev_char = cur_char

        return img

    def draw_ft_bitmap(self, img, bitmap, pen, color):
        # type: (_np.ndarray, _ft.Bitmap, _ft.Vector(), ()) -> None
        '''
        draw each char
        :param bitmap: bitmap
        :param pen:    pen
        :param color:  pen color e.g.(0,0,255) - red
        :return:       image
        '''
        x_pos = pen.x >> 6
        y_pos = pen.y >> 6
        cols = bitmap.width
        rows = bitmap.rows

        glyph_pixels = bitmap.buffer

        for row in range(rows):
            for col in range(cols):
                cp = glyph_pixels[row*cols + col]
                if cp != 0 and y_pos+row < img.shape[0] \
                        and x_pos+col < img.shape[1]:
                    pix = img[y_pos + row][x_pos + col]
                    pix[0] = (color[0]*cp+pix[0]*(255-cp))/255
                    pix[1] = (color[1]*cp+pix[1]*(255-cp))/255
                    pix[2] = (color[2]*cp+pix[2]*(255-cp))/255
"""
