use crate::TensorType;

/// A row-major matrix of quantized rows, borrowed from model storage.
#[derive(Clone, Copy, Debug)]
pub struct Matrix<'a> {
    pub ty: TensorType,
    pub data: &'a [u8],
    pub rows: usize,
    pub cols: usize,
}

impl<'a> Matrix<'a> {
    /// Panics unless `data` holds exactly `rows` rows of `cols` elements.
    pub fn new(ty: TensorType, data: &'a [u8], rows: usize, cols: usize) -> Self {
        assert_eq!(
            cols % ty.block_len(),
            0,
            "{cols} columns is not a whole number of {ty} blocks"
        );
        let m = Matrix {
            ty,
            data,
            rows,
            cols,
        };
        assert_eq!(
            data.len(),
            rows * m.row_bytes(),
            "{ty} matrix {rows}x{cols} has the wrong byte size"
        );
        m
    }

    pub fn row_bytes(&self) -> usize {
        self.cols / self.ty.block_len() * self.ty.block_bytes()
    }

    /// The first `rows` rows.
    pub fn top_rows(&self, rows: usize) -> Matrix<'a> {
        let rows = rows.min(self.rows);
        Matrix {
            ty: self.ty,
            data: &self.data[..rows * self.row_bytes()],
            rows,
            cols: self.cols,
        }
    }

    pub fn row(&self, r: usize) -> &'a [u8] {
        let n = self.row_bytes();
        &self.data[r * n..(r + 1) * n]
    }
}
