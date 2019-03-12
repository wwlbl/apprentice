import numpy as np
import apprentice

from apprentice import RationalApproximation
class RationalApproximationONB(object):
# class Raider(object):
    """
    Rational interpolation with degree reduction.
    """
    def __init__(self, X=None, Y=None, order=(2,1), fname=None, initDict=None, strategy=2, scale_min=-1, scale_max=1, pnames=None, tol=1e-14):
        """
        Multivariate rational approximation f(x)_mn =  g(x)_m/h(x)_n

        kwargs:
            fname --- to read in previously calculated Pade approximation

            X     --- anchor points
            Y     --- function values
            order --- tuple (m,n) m being the order of the numerator polynomial --- if omitted: auto
        """
        self.tol = tol
        self.validateSVD=True
        if initDict is not None:
            self.mkFromDict(initDict)
        elif fname is not None:
            self.mkFromJSON(fname)
        elif X is not None and Y is not None:
            self._m=order[0]
            self._n=order[1]
            self._scaler = apprentice.Scaler(np.atleast_2d(np.array(X, dtype=np.float64)), a=scale_min, b=scale_max, pnames=pnames)
            self._X   = self._scaler.scaledPoints
            self._dim = self._X[0].shape[0]
            # self._Y   = np.array(Y, dtype=np.float64)
            self._F = np.diag(Y)
            self._trainingsize=len(X)
            # if self._dim ==1:
                # self._ONB = apprentice.ONB([ [x] for x in self._X] )
            # else:
            self._ONB = apprentice.ONB(self._X)

            self.fit()
        else:
            raise Exception("Constructor not called correctly, use either fname, initDict or X and Y")

    @property
    def asDict(self):
        return {
                "CNUM": self._cnum.tolist(),
                "CDEN": self._cden.tolist(),
                "m": self._m,
                "n": self._n,
                "ONB": self._ONB.asDict,
                "scaler" : self._scaler.asDict
                }

    def save(self, fname):
        import json
        with open(fname, "w") as f:
            json.dump(self.asDict, f, indent=4)

    def mkFromDict(self, RDict):
        self._cnum = np.array(RDict["CNUM"])
        self._cden = np.array(RDict["CDEN"])
        self._m = int(RDict["m"])
        self._n = int(RDict["n"])
        self._scaler = apprentice.Scaler(RDict["scaler"])
        self._ONB = apprentice.ONB(RDict["ONB"])

    def mkFromJSON(self, fname):
        import json
        with open(fname, "r") as f:
            self.mkFromDict( json.load(f) )

    def fit(self):
        self._calc(self._m, self._n, self._ONB.Q)

    @property
    def F(self): return self._F


    def isViable(self, F, Q, m, n):
        """
        Solve the SVD and test the ratio of the first and last sv against tol
        """
        if n <0: return False
        S = self._svd(F, Q, m, n)
        dec = S['s'][-1] < self.tol * S['s'][0]
        print("Reductio: Testing orders",m,n, "decision: ", dec, "SVs",S['s'])

        return dec

    def _reduce(self, Q, M, N):
        """
        Denominator first reduction
        """
        m, n = M, N
        while self.isViable(self.F,  Q, m, n-1):
            n-=1

        # Numerator reduction
        Y = np.diagonal(self.F)

        if all([y==0 for y in Y]): return 0, 0


        if any([y == 0 for y in Y]):
            iF=np.diag([1./y for y in Y if not y==0]) # TODO move into reduction step and exclude 0s
        else:
            iF=np.diag([1./y for y in Y]) # TODO move into reduction step and exclude 0s

        while self.isViable(iF, Q[np.where(Y!=0)], n, m-1):
            m-=1
        return m, n

    def _calc(self, M, N, Q):
        """
        Perform the rational approxiation here.
        """

        # Degree reduction
        if self.tol>0:
            m, n = self._reduce(Q, M, N)
            print("Final degrees: m={} n={}".format(m,n))
        else: m, n = M, N

        # if m<M or n<N:
            # print("calculating reduced QR for max order %i"%max(m,n))
            # # a, b = self._ONB(max(m,n))
            # self._ONB._reduce(max(m,n))
        self._m = m
        self._n = n
        S = self._svd(self.F, Q, m, n)
        self._cnum = S["a"]
        self._cden = S["b"]
        self._svs = S["s"]
        del self._F

    @property
    def svs(self):
        """
        Return the singular values
        """
        return self._svs

    def _svd(self, F, Q, m, n):
        from scipy.special import comb
        Mdof = int(comb(self._dim + m, m))
        Ndof = int(comb(self._dim + n, n))
        dof = Mdof + Ndof

        if self.F.shape[0] < dof:
            raise Exception("SVD for m=%i, n=%i is underdetermined (requires %i inputs. You have %i.). Either reduce the polynomial degrees or increase input."%(m,n,dof,self.F.shape[0]))

        a = np.zeros((Mdof,1))
        b = np.zeros((Ndof,1))

        indM=range(Mdof)
        indN=range(Ndof)
        Z = np.dot(Q[:,indM].transpose(),  np.dot(F, Q[:,indN]))
        from scipy import linalg
        # print "Shape of matrix for SVD:", (np.dot(Q[:,indM],Z) - np.dot(F,Q[:,indN])).shape
        U, s, W = linalg.svd(np.dot(Q[:,indM],Z) - np.dot(F,Q[:,indN]), lapack_driver="gesvd") # Use the same driver as MATLAB here
        # from IPython import embed
        # embed()
        if self.validateSVD:
            S=np.zeros((U.shape[0], W.shape[0]))
            S[:s.shape[0], :s.shape[0]] = np.diag(s)
            if not np.allclose(np.dot(Q[:,indM],Z) - np.dot(F,Q[:,indN]), np.dot(U, np.dot(S, W))):
                raise Exception("SVD reco did not work")
        try:
            b[indN] = W[-1].reshape(b[indN].shape) # In python, the right singular values are in rows
        except Exception as e:
            print(e)
        a[indM] = np.dot(Z,b[indN])
        return {"Z":Z, "U":U, "s":s, "W":W, "a":a, "b":b}

    # NOTE not tested --- also mind that these expect x to be scaled aready
    def denom(self, x):
        """
        Return the value of the denominator polynomial at x
        """
        recDen = self._ONB._recurrence(x, len(self._cden))
        return float(np.dot(recDen,self._cden))

    # NOTE not tested --- also mind that these expect x to be scaled aready
    def numer(self, x):
        """
        Return the value of the numerator polynomial at x
        """
        recNum = self._ONB._recurrence(x, len(self._cnum))
        return float(np.dot(recNum,self._cnum))



    def predict(self, X):
        """
        Return the prediction of the RationalApproximation at X.
        NOTE X lives in the real world
        """
        X=self._scaler.scale(np.array(X))
        recNum = self._ONB._recurrence(X, len(self._cnum))
        recDen = self._ONB._recurrence(X, len(self._cden))
        return float(np.dot(recNum,self._cnum)/np.dot(recDen,self._cden))

    def __call__(self, X):
        """
        Operator version of predict.
        """
        return self.predict(X)


    def __str__(self):
        s="Rational approximation (%i, %i)"%(self._m, self._n)
        return s


if __name__== "__main__":
    np.random.seed(1)

    XMAX=10
    NPOINTS=20

    X = np.linspace(0.1, XMAX, NPOINTS)
    Y = 1./X
    R = np.random.normal(1,0.05, NPOINTS)
    Y = R*Y

    X=np.array([[x] for x in X])

    rrr = RationalApproximationONB(X=X, Y=Y, order=(3,1))
    rrr = RationalApproximationONB(X=X, Y=Y, order=(3,1), tol=-1)

    # Restore test
    rrr.save("testraONB.json")
    rrr = RationalApproximationONB(fname="testraONB.json")

    X2 = np.linspace(0.1, XMAX, NPOINTS*10)
    Y2 = [rrr(x) for x in X2]

    import pylab
    pylab.plot(X,Y, "bo")
    pylab.plot(X2,Y2, "r-")
    pylab.savefig("testraONB.pdf")